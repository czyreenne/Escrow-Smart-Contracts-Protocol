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

""" methods """
# log result to json
def log_result(operation, success, error_msg="", escrow_addr=""):
    """Log each operation to results"""
    result = {
        "timestamp": datetime.now().isoformat(),
        "escrow_addr": escrow_addr,
        "operation": operation,
        "success": success,
        "error": error_msg if not success else None
    }
    fuzz_results.append(result)
    print(f"[{len(fuzz_results)}] {operation} → {'✅' if success else '❌'}{error_msg[:50]}...")

# sim tx before executing to save gas irl
def simulate_tx(contract, function, *args, from_addr=None, value=0):
    """Pre-simulate transaction to catch reverts before sending"""
    try:
        fn = getattr(contract.functions, function)
        
        # Build FULL tx context for accurate simulation
        nonce = w3.eth.get_transaction_count(from_addr or buyer.address)
        call_opts = {
            'from': from_addr or buyer.address,
            'value': value,
            'gas': 500000,
            'gasPrice': w3.to_wei('20', 'gwei'),
            'nonce': nonce
        }
        
        # Now catches SPECIFIC reverts like "only seller can release"
        result = fn(*args).call(call_opts)
        return True
        
    except ContractLogicError as e:
        print(f"PRE-SIM FAIL {function}: {e}")
        return False
    except Exception as e:
        # Extract specific revert reason from generic VM Exception
        if 'VM Exception while processing transaction: revert' in str(e):
            print(f"PRE-SIM FAIL {function}: generic revert (likely auth/state)")
        else:
            print(f"PRE-SIM ERROR {function}: {e}")
        return False

def safe_tx(escrow, fn_name, *args, from_addr=buyer.address, value=0, signer_priv=buyer_priv, escrow_addr=""):
    """Build, sign, send tx only if pre-sim passes - WITH LOGGING"""
    fn = getattr(escrow.functions, fn_name)
    
    # Pre-simulate + log
    if not simulate_tx(escrow, fn_name, *args, from_addr=from_addr, value=value):
        log_result(fn_name, False, "PRE-SIM FAIL", escrow_addr)
        return None
    
    # Build and send
    nonce = w3.eth.get_transaction_count(from_addr)
    gas_price = w3.to_wei("20", "gwei")
    gas = 2000000
    
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
        log_result(fn_name, False, "POST-SIM REVERT", escrow_addr)
        print(f"❌ {fn_name} reverted after sim pass")
        return None

def fuzz_iteration(): 
    # NEW : 6-TUPLE DEPLOYMENT (Escrow + ConditionVerifier + Condition)
    escrow_addr, escrow_abi, cv_addr, cv_abi, condition_id, w3_fuzzer = deploy_escrow_with_verifier(
        seller.address,           # seller
        random.randint(3600, 7200), # timeout
        buyer.address,           # beneficiary  
        w3.to_wei(1, 'ether')    # required_amount
    )
    escrow = w3.eth.contract(address=escrow_addr, abi=escrow_abi)
    
    # Generate odd data upfront for conditions
    num_conditions = random.randint(0, 10)
    odd_conditions = []
    for i in range(num_conditions):
        odd_descs = [
            '',                                              # empty
            'a' * random.randint(90, 100),                   # max length overflow
            ''.join(random.choices('☃★♠™€∂£', k=50)),       # unicode/special chars
            ''.join(random.choices('0123456789', k=50)),     # numbers only
            'x' * random.randint(1, 89),                     # normal but random
        ]
        odd_conditions.append(random.choice(odd_descs))
    
    # Define all possible operations as callables (MULTIPLE INSTANCES!)
    operations = []
    
    # Multiple deposit attempts (0-3 different amounts)
    num_deposits = random.randint(0, 3)
    for _ in range(num_deposits):
        deposit_value = w3.to_wei(random.uniform(0.000001, 10), 'ether')
        operations.append(lambda v=deposit_value: safe_tx(escrow, "deposit", 
                                                         value=v, 
                                                         from_addr=buyer.address, 
                                                         signer_priv=buyer_priv,
                                                         escrow_addr=escrow_addr))
    
    # Multiple add_conditions with ODD DATA (0-10)
    for desc in odd_conditions:
        operations.append(lambda d=desc: safe_tx(escrow, "add_conditions", d, 
                                                from_addr=buyer.address,
                                                escrow_addr=escrow_addr))
    
    # Multiple fulfill_condition (OOB + valid indices)
    num_fulfills = random.randint(0, num_conditions + 3)
    for _ in range(num_fulfills):
        condition_idx = random.randint(-5, num_conditions + 5)
        if condition_idx < 0: condition_idx = 0  # Vyper clamps
        operations.append(lambda idx=condition_idx: safe_tx(escrow, "fulfill_condition", idx,
                                                          from_addr=seller.address, 
                                                          signer_priv=seller_priv,
                                                          escrow_addr=escrow_addr))
    
    # Multiple release attempts
    for _ in range(random.randint(1, 3)):
        operations.append(lambda: safe_tx(escrow, "release", 
                                         from_addr=seller.address, 
                                         signer_priv=seller_priv,
                                         escrow_addr=escrow_addr))
    
    # Multiple refund attempts (with time advance)
    for _ in range(random.randint(0, 2)):
        operations.append(lambda: (
            w3.provider.make_request("evm_increaseTime", [7200]),
            w3.provider.make_request("evm_mine", []),
            safe_tx(escrow, "refund", from_addr=buyer.address, signer_priv=buyer_priv, escrow_addr=escrow_addr)
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
    recent_ops = [r for r in fuzz_results[-20:] if "iteration" not in r.get("operation", "")]
    iteration_success_rate = sum(1 for r in recent_ops if r.get("success", False)) / max(1, len(recent_ops))
    
    fuzz_results.append({
        "iteration": len([r for r in fuzz_results if "iteration" in r]) + 1,
        "escrow_addr": escrow_addr,
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
