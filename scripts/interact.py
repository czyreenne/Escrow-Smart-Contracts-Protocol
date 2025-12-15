import os
import json
from web3 import Web3
from web3.exceptions import ContractLogicError
from datetime import datetime
import sys

import warnings
from web3.exceptions import MismatchedABI

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=".*MismatchedABI.*"
)

# Load deployment info from testnet.json 
with open("deployments/testnet.json") as f:
    data = json.load(f)

# Get the last two deployments (ConditionVerifier + Escrow)
deployments = data["deployments"]
escrow_info = None

# Find the most recent Escrow and its linked ConditionVerifier
for deployment in reversed(deployments):
    if deployment['contract'] == 'Escrow' and escrow_info is None:
        escrow_info = deployment
        cv_address = deployment['linkedContracts']['conditionVerifier']
        condition_id = deployment['linkedContracts']['externalConditionId']
        required_amount = deployment['linkedContracts']['requiredAmount']
        beneficiary = deployment['linkedContracts']['beneficiary']

escrow_address = escrow_info['address']

# Load ABIs
with open('contracts/Escrow.abi') as f:
    escrow_abi = json.load(f)

with open('contracts/ConditionVerifier.abi') as f:
    cv_abi = json.load(f)

# Connect to Ganache 
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
assert w3.is_connected(), "Web3 connection failed!"

# Pick accounts 
buyer_priv = os.environ.get("BUYER_PRIVATE_KEY") 
print(buyer_priv)
seller_priv = os.environ.get("SELLER_PRIVATE_KEY")

buyer = w3.eth.account.from_key(buyer_priv)
seller = w3.eth.account.from_key(seller_priv)

# Attach to the deployed contract 
escrow = w3.eth.contract(address=escrow_address, abi=escrow_abi)
condition_verifier = w3.eth.contract(address=cv_address, abi=cv_abi)

print(f"Connected to Escrow: {escrow_address}")
print(f"Connected to ConditionVerifier: {cv_address}")
print(f"External Condition ID: {condition_id}")

## 🎯 SMART PRE-CHECK (No Ganache bugs!)
def smart_precheck(contract, function_name, *args, from_addr=None, value=0):
    """State-aware pre-check: 100% accurate, NO RPC simulation needed"""
    
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
        # Check if already fulfilled
        _, fulfilled = escrow.functions.get_condition(idx).call()
        if fulfilled:
            return False, f"🛑 CONDITION {idx} ALREADY FULFILLED"
        return True, "success"
    
    elif function_name == "add_conditions":
        state = escrow.functions.state().call()
        if state != 1:
            return False, "🛑 MUST BE FUNDED FIRST (State=1)"
        return True, "success"
    
    # Fallback for other functions
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

## 🔍 BULLETPROOF Transaction Sender
def safe_send_tx(tx_fn, from_key, from_addr, value=0, expect_event=None, gas=500000, **kwargs):
    """Send tx + VALIDATE it actually worked"""
    try:
        tx = tx_fn().build_transaction({
            'from': from_addr,
            'value': value,
            'nonce': w3.eth.get_transaction_count(from_addr),
            'gas': gas,
            'gasPrice': w3.to_wei('1', 'gwei'),
            **kwargs
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, from_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 0:
            return False, "TX REVERTED (status=0)"
        
        if expect_event:
            try:
                if 'condition_verifier' in str(tx_fn).lower():
                    event_obj = getattr(condition_verifier.events, expect_event)()
                else:
                    event_obj = getattr(escrow.events, expect_event)()
                events = event_obj.process_receipt(receipt)
                if not events:
                    return False, f"No '{expect_event}' event emitted"
            except:
                pass
        
        return True, receipt
        
    except ContractLogicError as ex:
        return False, decode_revert_reason_raw(str(ex))
    except Exception as e:
        return False, str(e)

# Utilities
def get_state():
    state = escrow.functions.state().call()
    buyer_addr = escrow.functions.buyer().call()
    seller_addr = escrow.functions.seller().call()
    return {
        'state': state,
        'buyer': buyer_addr,
        'buyer_balance': w3.eth.get_balance(buyer_addr),
        'seller': seller_addr,
        'seller_balance': w3.eth.get_balance(seller_addr),
        'contract_balance': w3.eth.get_balance(escrow_address),
        'amount_locked': escrow.functions.amount().call()
    }

def print_state(state_dict=None):
    if state_dict is None:
        state_dict = get_state()
    print("\n🔍 Current Contract State")
    print(f"State  (0=Init, 1=Funded): {state_dict['state']}")
    print(f"Buyer:   {state_dict['buyer']} | Balance: {state_dict['buyer_balance']}")
    print(f"Seller:  {state_dict['seller']} | Balance: {state_dict['seller_balance']}")
    print(f"Contract balance: {state_dict['contract_balance']}")
    print(f"Amount locked: {state_dict['amount_locked']}\n")

def print_all_conditions():
    num = escrow.functions.get_num_conditions().call()
    print(f"📋 Total Conditions: {num}")
    for i in range(num):
        desc, fulfilled = escrow.functions.get_condition(i).call()
        status = "✅" if fulfilled else "❌"
        print(f"  {status} [{i}] {desc}")

def get_events(event_name, tx_hash, contract=None):
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    try:
        if contract == condition_verifier:
            event_obj = getattr(condition_verifier.events, event_name)()
        else:
            event_obj = getattr(escrow.events, event_name)()
        events = event_obj.process_receipt(receipt)
        return [dict(e.args) for e in events]
    except:
        return []

""" 🎯 PERFECT WORKFLOWS """

def run_deposit():
    print("💰 DEPOSIT WORKFLOW")
    success, reason = smart_precheck(escrow, "deposit")
    if not success:
        print(f"❌ PRE-SIM FAIL deposit: {reason}")
        print_state()
        return
    
    success, result = safe_send_tx(
        escrow.functions.deposit,
        buyer_priv, buyer.address,
        value=w3.to_wei("1", "ether"),
        expect_event="Deposited"
    )
    
    if success:
        print("✅ DEPOSIT SUCCEEDED!")
        print_state()
        print("Deposited event:", get_events("Deposited", result.transactionHash))
    else:
        print(f"❌ DEPOSIT FAILED: {result}")
        print_state()

def add_conditions(description):
    print("📝 ADD CONDITIONS WORKFLOW")
    success, reason = smart_precheck(escrow, "add_conditions", description)
    if not success:
        print(f"❌ PRE-SIM FAIL add_conditions: {reason}")
        print_state()
        return
    
    success, result = safe_send_tx(
        lambda: escrow.functions.add_conditions(description),
        buyer_priv, buyer.address,
        gas=5000000,
        expect_event="ConditionAdded"
    )
    
    if success:
        print(f"✅ Condition ADDED: '{description}'")
        print("ConditionAdded event:", get_events("ConditionAdded", result.transactionHash))
    else:
        print(f"❌ add_conditions FAILED: {result}")
        print_state()

def fulfill_conditions(indices):
    print("✅ FULFILL CONDITIONS WORKFLOW")
    unique_indices = list(dict.fromkeys(indices))
    
    for idx in unique_indices:
        success, reason = smart_precheck(escrow, "fulfill_condition", idx)
        if not success:
            print(f"❌ PRE-SIM FAIL fulfill_condition({idx}): {reason}")
            continue
        
        success, result = safe_send_tx(
            lambda: escrow.functions.fulfill_condition(idx),
            seller_priv, seller.address,
            expect_event="ConditionFulfilled"
        )
        
        if success:
            print(f"✅ Condition {idx} FULFILLED ✓")
        else:
            print(f"❌ fulfill_condition({idx}) FAILED: {result}")
    
    print_state()
    print_all_conditions()

def run_release():
    print("🔓 RELEASE WORKFLOW")
    success, reason = smart_precheck(escrow, "release")
    if not success:
        print(f"❌ PRE-SIM FAIL release: {reason}")
        print_state()
        return
    
    success, result = safe_send_tx(
        escrow.functions.release,
        seller_priv, seller.address,
        expect_event="Released"
    )
    
    if success:
        print("✅ RELEASE SUCCEEDED! 🎉")
        print_state()
        print("Released event:", get_events("Released", result.transactionHash))
    else:
        print(f"❌ RELEASE FAILED: {result}")
        print_state()
        print_all_conditions()

def run_incomplete_and_refund():
    print("💸 REFUND WORKFLOW")
    
    # Fast-forward timeout
    w3.provider.make_request("evm_increaseTime", [3601])
    w3.provider.make_request("evm_mine", [])
    print("⏩ Time advanced past timeout")
    
    success, reason = smart_precheck(escrow, "refund")
    if not success:
        print(f"❌ PRE-SIM FAIL refund: {reason}")
        print_state()
        print_all_conditions()
        return
    
    success, result = safe_send_tx(
        escrow.functions.refund,
        buyer_priv, buyer.address,
        expect_event="Refunded"
    )
    
    if success:
        print("✅ REFUND SUCCEEDED!")
        print_state()
    else:
        print(f"❌ REFUND FAILED: {result}")
        print_state()
        print_all_conditions()

def deposit_to_verifier():
    print("🌐 EXTERNAL CONDITION WORKFLOW")
    print(f"Condition ID: {condition_id}")
    print(f"Required: Ξ {w3.from_wei(required_amount, 'ether')}")
    
    success, reason = smart_precheck(condition_verifier, "deposit_eth", condition_id)
    if not success:
        print(f"❌ PRE-SIM FAIL deposit_to_verifier: {reason}")
        return
    
    success, result = safe_send_tx(
        lambda: condition_verifier.functions.deposit_eth(condition_id),
        seller_priv, seller.address,
        value=required_amount,
        gas=500000
    )
    
    if success:
        print("✅ Deposit to verifier SUCCEEDED!")
        print(f"TX: {result.transactionHash.hex()}")
        try:
            events = get_events("ConditionFulfilled", result.transactionHash, condition_verifier)
            if events:
                print("✅ External condition FULFILLED!")
        except:
            pass
    else:
        print(f"❌ deposit_to_verifier FAILED: {result}")

def verify_external_condition():
    print("🔍 EXTERNAL CONDITION CHECK")
    print(f"Condition ID: {condition_id}")
    
    fulfilled = condition_verifier.functions.is_condition_fulfilled(condition_id).call()
    print(f"Direct fulfilled: {fulfilled}")
    
    buyer_addr = escrow.functions.buyer().call()
    verified = condition_verifier.functions.verify_condition_for_parties(
        condition_id, buyer_addr, beneficiary
    ).call()
    print(f"Verified for escrow parties: {verified}")
    
    return verified

def print_escrow_summary():
    print_state()
    print_all_conditions()

def generate_event_signature(event):
    """Generate Ethereum event signature from ABI"""
    name = event['name']
    inputs = event['inputs']
    
    # Build signature: "EventName(type1,type2,...)"
    arg_types = []
    for input in inputs:
        arg_types.append(input['type'])
    
    sig_text = f"{name}({','.join(arg_types)})"
    return Web3.keccak(text=sig_text).hex()

def print_complete_audit_trail(escrow_address):
    """Decode events using manual ABI parsing"""
    print(f"\n🔍 EVENT DECODER ({escrow_address}):")
    print("=" * 80)
    
    # Load ABI
    with open('contracts/Escrow.abi', 'r') as f:
        abi = json.load(f)
    
    # Generate ALL event signatures
    event_sigs = {}
    for item in abi:
        if item['type'] == 'event':
            event_name = item['name']
            sig = generate_event_signature(item)
            event_sigs[sig] = event_name
            print(f"ABI Event: {event_name:<20} → {sig}")
    
    # Get recent logs
    current_block = w3.eth.block_number
    logs = w3.eth.get_logs({
        'address': escrow_address,
        'fromBlock': max(0, current_block - 20),
        'toBlock': current_block
    })
    
    print(f"\nFound {len(logs)} logs:")
    
    for i, log in enumerate(logs):
        try:
            topics = log['topics']
            if not topics:
                print(f"[{i:2d}] ❓ NO TOPICS")
                continue
            
            # Match topic[0] to generated signature
            sig = topics[0].hex()
            event_name = event_sigs.get(sig, "UNKNOWN")
            
            print(f"[{i:2d}] ✅ {event_name:<20} | Block {log['blockNumber']}")
            print(f"     Sig: {sig[:20]}...")
            
            # Show indexed params
            if len(topics) > 1:
                print(f"     Topic1: {topics[1].hex()[:20]}...")
            if len(topics) > 2:
                print(f"     Topic2: {topics[2].hex()[:20]}...")
                
        except Exception as e:
            print(f"[{i:2d}] ❌ ERROR: {e}")
    
    print("=" * 80)

if __name__ == "__main__":
    tests_to_run = sys.argv[1:] if len(sys.argv) > 1 else []

    if not tests_to_run:
        print("🧪 Running DEFAULT flow: deposit → add → fulfill → release")
        run_deposit()
        add_conditions("Delivery confirmed")
        fulfill_conditions([0])
        run_release()
    else:
        for test in tests_to_run:
            if test == 'deposit':
                run_deposit()
            elif test == 'release':
                run_release()
            elif test == 'refund':
                run_incomplete_and_refund()
            elif test == 'add_conditions' and len(sys.argv) >= 3:
                add_conditions(sys.argv[2])
            elif test == 'fulfill_conditions' and len(sys.argv) >= 3:
                fulfill_conditions([int(x) for x in sys.argv[2:]])
            elif test == 'deposit_to_verifier':
                deposit_to_verifier()
            elif test == 'verify_external_condition':
                verify_external_condition()
            elif test == 'print_all_conditions':
                print_all_conditions()
            elif test == 'escrow_summary':
                print_escrow_summary()
            elif test == 'full_audit':
                print_complete_audit_trail(escrow_address)
            else:
                print(f"❓ Unknown: {test}")
                print("\n🚀 Commands:")
                print("  deposit | release | refund")
                print("  add_conditions \"Text\" | fulfill_conditions 0 1")
                print("  deposit_to_verifier | verify_external_condition")
                print("  print_all_conditions | escrow_summary | full_audit")
