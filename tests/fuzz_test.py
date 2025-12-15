import os, sys, json
from web3 import Web3
from web3.exceptions import ContractLogicError
from datetime import datetime
from test_deploy import deploy_escrow_with_verifier  
import random

# save results to json
RESULTS_FILE = f"fuzz_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
fuzz_results = []

# w3 setup
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
assert w3.is_connected(), "Web3 connection failed!"
buyer_priv = os.environ.get("BUYER_PRIVATE_KEY")
seller_priv = os.environ.get("SELLER_PRIVATE_KEY")
buyer = w3.eth.account.from_key(buyer_priv)
seller = w3.eth.account.from_key(seller_priv)

""" 🎯 SMART PRE-CHECK + VYPER REVERT DECODER (Ganache-proof!) """
def smart_precheck(escrow, cv_contract, function_name, *args, from_addr=None, value=0, is_cv=False):
    """State-aware pre-check: 100% accurate, NO RPC simulation bugs"""
    from_addr = from_addr or buyer.address
    
    if is_cv:  # ConditionVerifier functions
        if function_name == "deposit_eth":
            if not args:
                return False, "🛑 NO CONDITION_ID PROVIDED"
            condition_id = args[0]
            # Check if already fulfilled
            try:
                fulfilled = cv_contract.functions.is_condition_fulfilled(condition_id).call()
                if fulfilled:
                    return False, f"🛑 CONDITION {condition_id} ALREADY FULFILLED"
            except:
                pass
            return True, "success"
        return True, "success"
    
    # Escrow functions (existing logic)
    if function_name == "deposit":
        state = escrow.functions.state().call()
        if state == 1:
            return False, "🛑 ALREADY FUNDED (State=1)"
        return True, "success"
    
    elif function_name == "release":
        state = escrow.functions.state().call()
        if state != 1:
            return False, "🛑 NOT FUNDED (State≠1)"
        return True, "success (conditions checked by real tx)"
    
    elif function_name == "refund":
        state = escrow.functions.state().call()
        if state != 1:
            return False, "🛑 NOT FUNDED (State≠1)"
        return True, "success (timeout checked by real tx)"
    
    elif function_name == "fulfill_condition":
        if not args:
            return False, "🛑 NO INDEX PROVIDED"
        idx = args[0]
        num_conditions = escrow.functions.get_num_conditions().call()
        if idx < 0 or idx >= num_conditions:
            return False, f"🛑 INDEX OUT OF BOUNDS ({idx} >= {num_conditions})"
        _, fulfilled = escrow.functions.get_condition(idx).call()
        if fulfilled:
            return False, f"🛑 CONDITION {idx} ALREADY FULFILLED"
        return True, "success"
    
    elif function_name == "add_conditions":
        state = escrow.functions.state().call()
        if state != 1:
            return False, "🛑 MUST BE FUNDED FIRST (State=1)"
        return True, "success"
    
    return True, "success"

def decode_revert_reason_raw(revert_data: str) -> str:
    """Decode Vyper assert from real tx reverts"""
    if not revert_data or revert_data == '0x':
        return "generic revert"
    
    try:
        data_bytes = bytes.fromhex(revert_data[2:] if revert_data.startswith('0x') else revert_data)
        if data_bytes[:4] == b'\x08\xc3\x79\xa0':
            offset = int.from_bytes(data_bytes[4:36], 'big')
            length = int.from_bytes(data_bytes[offset:offset+32], 'big')
            message = data_bytes[offset+32:offset+32+length].decode('utf-8')
            return f"🛑 VYPER ASSERT: '{message}'"
    except:
        pass
    
    return f"raw revert: {revert_data[:50]}..."

""" BULLETPROOF Transaction Sender (Escrow + ConditionVerifier) """
def safe_tx(escrow, cv_contract, fn_name, *args, from_addr=buyer.address, value=0, 
            signer_priv=buyer_priv, escrow_addr="", is_cv=False):
    """Build, sign, send tx + VALIDATE with smart pre-check"""
    
    # 🎯 SMART PRE-CHECK FIRST
    success, reason = smart_precheck(escrow, cv_contract, fn_name, *args, from_addr, value, is_cv)
    if not success:
        log_result(f"{fn_name}_PRECHECK_FAIL", False, reason, escrow_addr)
        print(f"PRE-SIM FAIL {fn_name}: {reason}")
        return None
    
    # Determine target contract and function
    target_contract = cv_contract if is_cv else escrow
    fn = getattr(target_contract.functions, fn_name)
    nonce = w3.eth.get_transaction_count(from_addr)
    gas_price = w3.to_wei("20", "gwei")
    gas = 2000000
    
    try:
        tx = fn(*args).build_transaction({
            "from": from_addr,
            "value": value,
            "nonce": nonce,
            "gas": gas,
            "gasPrice": gas_price
        })
        
        signed = w3.eth.account.sign_transaction(tx, signer_priv)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            log_result(fn_name, True, "", escrow_addr)
            print(f"✅ {fn_name} succeeded")
            return receipt
        else:
            # 🔍 POST-TX DIAGNOSIS
            if fn_name == "release":
                num_conditions = escrow.functions.get_num_conditions().call()
                all_fulfilled = escrow.functions.all_conditions_fulfilled().call({'from': seller.address})
                if num_conditions > 0 and not all_fulfilled:
                    reason = "🛑 NOT ALL CONDITIONS FULFILLED"
                else:
                    reason = "🛑 EXTERNAL CONDITION FAILED"
            elif fn_name == "deposit_eth":
                condition_id = args[0] if args else 0
                try:
                    fulfilled = cv_contract.functions.is_condition_fulfilled(condition_id).call()
                    reason = f"🛑 CONDITION {condition_id} NOT FULFILLED" if not fulfilled else "🛑 UNKNOWN CV REVERT"
                except:
                    reason = "🛑 CV REVERT"
            else:
                reason = "🛑 TX REVERTED"
            
            log_result(fn_name, False, reason, escrow_addr)
            print(f"❌ {fn_name} TX REVERTED: {reason}")
            return None
            
    except ContractLogicError as ex:
        reason = decode_revert_reason_raw(str(ex))
        log_result(fn_name, False, reason, escrow_addr)
        print(f"❌ {fn_name} VYPER ERROR: {reason}")
        return None
    except Exception as e:
        reason = str(e)
        log_result(f"{fn_name}_CRASH", False, reason, escrow_addr)
        print(f"❌ {fn_name} CRASH: {reason}")
        return None

# log result to json with pattern detection
def log_result(operation, success, error_msg="", escrow_addr=""):
    """Log each operation to results with pattern highlighting"""
    result = {
        "timestamp": datetime.now().isoformat(),
        "escrow_addr": escrow_addr,
        "operation": operation,
        "success": success,
        "error": error_msg if not success else None
    }
    fuzz_results.append(result)
    
    status = '✅' if success else '❌'
    msg_preview = (error_msg[:60] + "..." if error_msg else "").replace("🛑 VYPER ASSERT: '", "")
    
    if "conditions" in msg_preview.lower():
        msg_preview = "🔄 " + msg_preview
    elif "index" in msg_preview.lower() or "bounds" in msg_preview.lower():
        msg_preview = "📏 " + msg_preview
    elif "funded" in msg_preview.lower():
        msg_preview = "💰 " + msg_preview
    elif "external" in msg_preview.lower():
        msg_preview = "🔗 " + msg_preview
    elif "deposit_eth" in operation:
        msg_preview = "🌐 " + msg_preview
    
    print(f"[{len(fuzz_results)}] {operation} → {status} {msg_preview}")

def fuzz_iteration(): 
    # 6-TUPLE DEPLOYMENT (Escrow + ConditionVerifier + Condition)
    escrow_addr, escrow_abi, cv_addr, cv_abi, condition_id, w3_fuzzer = deploy_escrow_with_verifier(
        seller.address,             
        random.randint(3600, 7200), 
        buyer.address,              
        w3.to_wei(1, 'ether')       
    )
    escrow = w3.eth.contract(address=escrow_addr, abi=escrow_abi)
    cv_contract = w3.eth.contract(address=cv_addr, abi=cv_abi)
    
    log_result("DEPLOY", True, "", escrow_addr)
    print(f"🆕 Deployed: {escrow_addr} (CV: {cv_addr}, Cond: {condition_id})")
    
    # Generate odd data upfront for conditions
    num_conditions = random.randint(0, 10)
    odd_conditions = []
    for i in range(num_conditions):
        odd_descs = [
            '',                                    
            'a' * random.randint(90, 100),         
            ''.join(random.choices('☃★♠™€∂£', k=50)), 
            ''.join(random.choices('0123456789', k=50)), 
            'x' * random.randint(1, 89),           
        ]
        odd_conditions.append(random.choice(odd_descs))
    
    # Define all possible operations as callables (NOW WITH CV!)
    operations = []
    
    # 1. Multiple deposit attempts
    num_deposits = random.randint(0, 3)
    for _ in range(num_deposits):
        deposit_value = w3.to_wei(random.uniform(0.000001, 10), 'ether')
        operations.append(lambda v=deposit_value: safe_tx(escrow, cv_contract, "deposit", 
                                                         value=v, from_addr=buyer.address, 
                                                         signer_priv=buyer_priv, escrow_addr=escrow_addr))
    
    # 2. Multiple add_conditions with ODD DATA
    for desc in odd_conditions:
        operations.append(lambda d=desc: safe_tx(escrow, cv_contract, "add_conditions", d, 
                                                from_addr=buyer.address, escrow_addr=escrow_addr))
    
    # 3. Multiple fulfill_condition (OOB + valid)
    num_fulfills = random.randint(0, num_conditions + 3)
    for _ in range(num_fulfills):
        condition_idx = random.randint(-5, num_conditions + 5)
        if condition_idx < 0: condition_idx = 0
        operations.append(lambda idx=condition_idx: safe_tx(escrow, cv_contract, "fulfill_condition", idx,
                                                           from_addr=seller.address, 
                                                           signer_priv=seller_priv, escrow_addr=escrow_addr))
    
    # 4. Multiple deposit_to_verifier (under/over required amount)
    num_cv_deposits = random.randint(0, 4)
    for _ in range(num_cv_deposits):
        cv_value = w3.to_wei(random.uniform(0.1, 3), 'ether')  # Sometimes under, sometimes over
        operations.append(lambda v=cv_value, cid=condition_id: safe_tx(escrow, cv_contract, "deposit_eth", cid,
                                                                      value=v, from_addr=seller.address, 
                                                                      signer_priv=seller_priv, 
                                                                      escrow_addr=escrow_addr, is_cv=True))
    
    # 5. Multiple release attempts
    for _ in range(random.randint(1, 3)):
        operations.append(lambda: safe_tx(escrow, cv_contract, "release", 
                                         from_addr=seller.address, signer_priv=seller_priv,
                                         escrow_addr=escrow_addr))
    
    # 6. Multiple refund attempts
    for _ in range(random.randint(0, 2)):
        operations.append(lambda: (
            w3.provider.make_request("evm_increaseTime", [7200]),
            w3.provider.make_request("evm_mine", []),
            safe_tx(escrow, cv_contract, "refund", from_addr=buyer.address, 
                    signer_priv=buyer_priv, escrow_addr=escrow_addr)
        )[2])
    
    # 🌀 Run 8-15 RANDOM operations in RANDOM ORDER
    num_ops = random.randint(8, 15)
    random.shuffle(operations)
    
    print(f"🌀 Running {num_ops} randomized ops (from {len(operations)} total ops)...")
    for i in range(num_ops):
        try:
            result = operations[i % len(operations)]()
        except Exception as e:
            log_result(f"OP_{i}_CRASH", False, str(e), escrow_addr)
    
    # Iteration summary
    recent_ops = [r for r in fuzz_results[-25:] if "iteration" not in r.get("operation", "")]
    iteration_success_rate = sum(1 for r in recent_ops if r.get("success", False)) / max(1, len(recent_ops))
    
    fuzz_results.append({
        "iteration": len([r for r in fuzz_results if "iteration" in r]) + 1,
        "escrow_addr": escrow_addr,
        "cv_addr": cv_addr,
        "condition_id": condition_id,
        "total_ops_attempted": num_ops,
        "total_ops_available": len(operations),
        "success_rate": float(iteration_success_rate)
    })
    
    print(f"📊 Iteration success rate: {iteration_success_rate:.1%}")
    print("=== Iteration complete ===\n")

# Run 150 fuzz iterations
for i in range(150):
    print(f"=== Fuzz iteration {i} ===")
    fuzz_iteration()

# FINAL SAVE
with open(RESULTS_FILE, 'w') as f:
    json.dump(fuzz_results, f, indent=2)
print(f"✅ Saved {len(fuzz_results)} results to {RESULTS_FILE}")
