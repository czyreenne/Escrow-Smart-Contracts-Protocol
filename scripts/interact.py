# TODO: To update interact.py
# NOTE: no need to print logged outputs since printing already built into deploy.py script.

import os
import json
from web3 import Web3
from web3.exceptions import ContractLogicError
from datetime import datetime
import sys

# Set up audit trail collector 
audit_trail = []

# Load deployment info from testnet.json 
with open("deployments/testnet.json") as f:
    data = json.load(f)

# Get the last two deployments (ConditionVerifier + Escrow)
deployments = data["deployments"]
escrow_info = None
cv_info = None 

# Find the most recent Escrow and its linked COnditionVerifier
for deployment in reversed(deployments):
    if deployment['contract'] == 'Escrow' and escrow_info is None:
        escrow_info = deployment
        # Get linked ConditionVerifier address
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
# Ganache accounts from its GUI/CLI. 
buyer_priv = os.environ.get("BUYER_PRIVATE_KEY")      # set these in your env before running script
seller_priv = os.environ.get("SELLER_PRIVATE_KEY")

buyer = w3.eth.account.from_key(buyer_priv)
seller = w3.eth.account.from_key(seller_priv)

# Attach to the deployed contract 
escrow = w3.eth.contract(address=escrow_address, abi=escrow_abi)
condition_verifier = w3.eth.contract(address=cv_address, abi=cv_abi)

print(f"Connected to Escrow: {escrow_address}")
print(f"Connected to ConditionVerifier: {cv_address}")
print(f"External Condition ID: {condition_id}")

# Utility function: Print escrow state & balances
def get_state():
    # Get all relevant on-chain values for immediate inspection / audit logs
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

def print_state(state_dict):
    print("\n Current Contract State")
    print(f"State  (0=Init, 1=Funded): {state_dict['state']}")
    print(f"Buyer:   {state_dict['buyer']} | Balance: {state_dict['buyer_balance']}")
    print(f"Seller:  {state_dict['seller']} | Balance: {state_dict['seller_balance']}")
    print(f"Contract balance: {state_dict['contract_balance']}")
    print(f"Amount locked: {state_dict['amount_locked']}\n")

def get_events(event_name, tx_hash):
    # This pulls event logs for a tx in a normalized format
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    events = getattr(escrow.events, event_name)().process_receipt(receipt)
    return [dict(e.args) for e in events]

# NEW: Added test for buyer to add conditions
def add_conditions(description):
    tx_add = escrow.functions.add_conditions(description).build_transaction({
        "from": buyer.address,
        "nonce": w3.eth.get_transaction_count(buyer.address),
        "gas": 2000000,
        "gasPrice": w3.to_wei("20", "gwei"),
    })
    signed_add = w3.eth.account.sign_transaction(tx_add, buyer_priv)
    tx_hash_add = w3.eth.send_raw_transaction(signed_add.raw_transaction)
    rcpt_add = w3.eth.wait_for_transaction_receipt(tx_hash_add)
    print(f"Condition added: {description}")
    # Optionally, print/log event data
    events = get_events("ConditionAdded", tx_hash_add)
    print("Added condition event:", events)

# NEW: Added check to print the full details of all conditions
def print_all_conditions():
    num = escrow.functions.get_num_conditions().call()
    print(f"Total Conditions: {num}")
    for i in range(num):
        desc, fulfilled = escrow.functions.get_condition(i).call()
        print(f"Condition {i}: {desc} | Fulfilled: {fulfilled}")

# NEW: Let's seller check if they have fulfilled all the conditions
def all_conditions_fulfilled():
    all_fulfilled = escrow.functions.all_conditions_fulfilled().call({
        "from": seller.address
    })
    if all_fulfilled:
        print("All conditions are fulfilled")
    else:
        print("Not all conditions are fulfilled. Please check with print_all_conditions()")

# NEW: Seller can fulfill specific conditions specified by the index in the input array
def fulfill_conditions(indices):
    seen = set()
    unique_indices = []
    for idx in indices:
        if idx not in seen:
            unique_indices.append(idx)
            seen.add(idx)
    for idx2 in unique_indices:
        try: 
            tx = escrow.functions.fulfill_condition(idx2).build_transaction({
                "from": seller.address,
                "nonce": w3.eth.get_transaction_count(seller.address),
                "gas": 100000,
                "gasPrice": w3.to_wei("200", "gwei")
            })
            signed_fulfill = w3.eth.account.sign_transaction(tx, seller_priv)
            tx_hash_fulfill = w3.eth.send_raw_transaction(signed_fulfill.raw_transaction)
            rcpt_fulfill = w3.eth.wait_for_transaction_receipt(tx_hash_fulfill)
            print(f"    Condition {idx2} fulfilled.")
        except Exception as ex:
            print(f"Error fulfilling condition {idx2}: {ex} ")
    state_dict = get_state()
    print_state(state_dict)
    print("Condition(s) fulfilled")

# 1. Deposit by Buyer 
def run_deposit():
    try:
        print("Running deposit workflow")
        print("\nDeposit event test: Buyer deposits to escrow\n")
        deposit_tx = escrow.functions.deposit().build_transaction({
            "from": buyer.address,
            "value": w3.to_wei("1", "ether"),  # 1 ETH deposit
            "nonce": w3.eth.get_transaction_count(buyer.address),
            "gas": 200000,
            "gasPrice": w3.to_wei("20", "gwei")
        })
        signed_deposit = w3.eth.account.sign_transaction(deposit_tx, buyer_priv)
        tx_hash_deposit = w3.eth.send_raw_transaction(signed_deposit.raw_transaction)
        rcpt_deposit = w3.eth.wait_for_transaction_receipt(tx_hash_deposit)
        state_dict = get_state()
        print_state(state_dict)
        deposited_events = get_events("Deposited", tx_hash_deposit)
        print("Checking for Deposited event...")
        print(deposited_events)
        # Audit trail append
        audit_trail.append({
            "step": "deposit",
            "tx_hash": tx_hash_deposit.hex(),
            "events": deposited_events,
            "state": state_dict,
            "status": rcpt_deposit.status
        })
    except ContractLogicError as ex:
        state_dict = get_state()
        print(f"Deposit failed due to contract logic: {ex}")
    except Exception as e:
        state_dict = get_state()
        print(f"Deposit attempt failed due to other error: {e}")

# 2. Seller releases funds (claim) 
def run_release():
    try:
        print("Running release workflow")
        print("\nRelease event test: Seller releases funds\n")
        release_tx = escrow.functions.release().build_transaction({
            "from": seller.address,
            "nonce": w3.eth.get_transaction_count(seller.address),
            "gas": 200000,
            "gasPrice": w3.to_wei("20", "gwei")
        })
        signed_release = w3.eth.account.sign_transaction(release_tx, seller_priv)
        tx_hash_release = w3.eth.send_raw_transaction(signed_release.raw_transaction)
        rcpt_release = w3.eth.wait_for_transaction_receipt(tx_hash_release)
        state_dict = get_state()
        print_state(state_dict)
        released_events = get_events("Released", tx_hash_release)
        print("Checking for Released event...")
        print(released_events)
        audit_trail.append({
            "step": "release",
            "tx_hash": tx_hash_release.hex(),
            "events": released_events,
            "state": state_dict,
            "status": rcpt_release.status
        })
    except ContractLogicError as ex:
        state_dict = get_state()
        print(f"Release failed due to contract logic: {ex}")
    except Exception as e:
        state_dict = get_state()
        print(f"Release attempt failed due to other error: {e}")

# 3. Partial fulfillment then refund before release
def run_incomplete_and_refund():
    print("\n=== Incomplete and Refund (Should NOT Succeed if running interact.py with no specifiers) ===")

    # Fast-forward time past timeout
    w3.provider.make_request("evm_increaseTime", [3601])
    w3.provider.make_request("evm_mine", [])

    # Now attempt refund as buyer
    try:
        refund_tx = escrow.functions.refund().build_transaction({
            "from": buyer.address,
            "nonce": w3.eth.get_transaction_count(buyer.address),
            "gas": 200000,
            "gasPrice": w3.to_wei("20", "gwei")
        })
        signed_refund = w3.eth.account.sign_transaction(refund_tx, buyer_priv)
        tx_hash_refund = w3.eth.send_raw_transaction(signed_refund.raw_transaction)
        rcpt_refund = w3.eth.wait_for_transaction_receipt(tx_hash_refund)
        state_after = get_state()
        print_state(state_after)
        if rcpt_refund.status== 1:
            print("Refund succeeded!")
        else:
            print("Refund failed. Transaction reverted.")
        audit_trail.append({
            "step": "incomplete_and_refund",
            "tx_hash": tx_hash_refund.hex(),
            "state": state_after,
            "status": rcpt_refund.status,
            "events": get_events("Refunded", tx_hash_refund)
        })
    except ContractLogicError as ex:
        current_state = get_state()
        fulfilled = []
        num_conditions = escrow.functions.get_num_conditions().call()
        for i in range(num_conditions):
            _desc, is_fulfilled = escrow.functions.get_condition(i).call()
            if is_fulfilled:
                fulfilled.append(i)
        audit_trail.append({
            "step": "incomplete_and_refund",
            "tx_hash": None,
            "state": current_state,
            "status": 0,
            "events": []
        })
        print(f"Refund failed due to contract logic: {ex}\nFulfilled conditions at failure: {fulfilled}")
    except Exception as e:
        current_state = get_state()
        audit_trail.append({
            "step": "incomplete_and_refund",
            "tx_hash": None,
            "state": current_state,
            "status": 0,
            "events": []
        })
        print(f"Refund attempt failed due to other error: {e}")

# ===== NEW: ConditionVerifier Interaction Functions =====

def deposit_to_verifier():
    """
    Seller deposits ETH to ConditionVerifier to fulfill external condition
    """
    try:
        print(f"\n=== Depositing to ConditionVerifier===")
        print(f"Condition ID: {condition_id}")
        print(f"Required Amount: {w3.from_wei(required_amount, 'ether')} ETH")
        print(f"Beneficiary: {beneficiary}")

        # Build deposit transaction
        deposit_tx = condition_verifier.functions.deposit_eth(condition_id).build_transaction({
            "from": seller.address,
            "value": required_amount,  # Use the required amount from deployment
            "nonce": w3.eth.get_transaction_count(seller.address),
            "gas": 300000,
            "gasPrice": w3.to_wei("20", "gwei")
        })
        
        signed_deposit = w3.eth.account.sign_transaction(deposit_tx, seller_priv)
        tx_hash = w3.eth.send_raw_transaction(signed_deposit.raw_transaction)
        print(f"TX Hash: {tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print("✅ Deposit successful!")
            
            # Check for ConditionFulfilled event
            fulfilled_events = condition_verifier.events.ConditionFulfilled().process_receipt(receipt)
            if fulfilled_events:
                print("✅ External condition automatically fulfilled!")
                print(f"   Event: {fulfilled_events[0]['args']}")
            else:
                print("⚠️  Condition not yet fulfilled (may need more deposits)")
                
            # Print beneficiary confirmation
            forwarded_events = condition_verifier.events.EthForwarded().process_receipt(receipt)
            if forwarded_events:
                print(f"💸 ETH forwarded to beneficiary: {forwarded_events[0]['args']['beneficiary']}")
        else:
            print("❌ Deposit failed")
            
    except Exception as e:
        print(f"Error depositing to verifier: {e}")

def verify_external_condition():
    """Check if external condition is fulfilled"""
    try:
        print(f"\n=== Checking External Condition Status ===")
        print(f"Condition ID: {condition_id}")
        
        # Use simple check instead of get_condition_status
        fulfilled = condition_verifier.functions.is_condition_fulfilled(condition_id).call()
        
        print(f"Fulfilled: {fulfilled}")
        
        # Verify for parties (what Escrow contract checks)
        seller_addr = escrow.functions.seller().call()
        buyer_addr = escrow.functions.buyer().call()
        
        verified = condition_verifier.functions.verify_condition_for_parties(
            condition_id,
            buyer_addr,  # Changed to buyer (the creator)
            beneficiary
        ).call()
        
        print(f"✓ Verified for Escrow parties: {verified}")
        
        if verified:
            print("✅ External condition ready - release() will succeed")
        else:
            print("❌ External condition not met - release() will fail")
            
        return verified
        
    except Exception as e:
        print(f"Error verifying condition: {e}")
        return False

def get_external_condition_details():
    """Get full details of the external condition"""
    print("\n⚠️  get_condition_details() temporarily disabled due to flag/enum issue")
    print("Use verify_external_condition() instead")
    return
    
    # Original code commented out for now
    # try:
    #     details = condition_verifier.functions.get_condition_details(condition_id).call()
    #     ...

# def get_condition_details():
#     """Get full details of the external condition"""
#     try:
#         print(f"\n=== External Condition Details ===")
        
#         details = condition_verifier.functions.get_condition_details(condition_id).call()
        
#         print(f"Condition Type: {details[0]}")  # ConditionType enum value
#         print(f"Creator: {details[1]}")
#         print(f"Beneficiary: {details[2]}")
#         print(f"Required Amount: {w3.from_wei(details[3], 'ether')} ETH")
#         print(f"Received Amount: {w3.from_wei(details[4], 'ether')} ETH")
#         print(f"Fulfilled: {details[5]}")
#         print(f"Disputed: {details[6]}")
#         print(f"Created At: {datetime.fromtimestamp(details[7])}")
        
#         if details[8] > 0:
#             print(f"Fulfilled At: {datetime.fromtimestamp(details[8])}")
#         else:
#             print("Fulfilled At: Not yet")
            
    # except Exception as e:
    #     print(f"Error getting condition details: {e}")


def print_escrow_summary():
    """Print compact escrow summary"""
    try:
        buyer_addr, seller_addr, state, amount, num_conds = escrow.functions.get_escrow_summary().call()
        
        print(f"\n=== Escrow Summary ===")
        print(f"Buyer: {buyer_addr}")
        print(f"Seller: {seller_addr}")
        print(f"State: {state} (0=Not Funded, 1=Funded)")
        print(f"Amount Locked: {w3.from_wei(amount, 'ether')} ETH")
        print(f"Manual Conditions: {num_conds}")
        
    except Exception as e:
        print(f"Error getting summary: {e}")

if __name__ == "__main__":
    # Usage: `python scripts/interact.py NAME_OF_STEP`
    #     python scripts/interact.py deposit           # (just runs deposit)
    #     python scripts/interact.py fulfill_all_conditions release  # (deposit, fulfill, then release)
    #     python scripts/interact.py partial_fulfillment_and_refund:NUMBER_OF_SCENARIOS_FULFILLED        # (just runs refund)

    # The Escrow contract `state` field means:
    #   0 = Init      (Contract is freshly deployed, no funds yet / Release or Refund has occured)
    #   1 = Funded    (Buyer has deposited funds, waiting for Release or Refund)

    # The transaction `status` field means:
    #   1 = Success   (Transaction executed and state changed as intended)
    #   0 = Failed    (Transaction reverted—an error, assert, or require failed; no state change except gas spent)

    tests_to_run = sys.argv[1:] if len(sys.argv) > 1 else []

    if not tests_to_run:
        run_deposit()
        num_conditions = escrow.functions.get_num_conditions().call()
        fulfill_conditions(list(range(num_conditions)))  # This fulfills all
        run_release()
        run_incomplete_and_refund()
    else:
        for test in tests_to_run:
            if test == 'add_conditions':
                if len(sys.argv) < 3:
                    print("Usage: python3 scripts/interact.py add_conditions \"Description text\"")
                    sys.exit(1)
                description = sys.argv[2]
                add_conditions(description)
            elif test == 'print_all_conditions':
                print_all_conditions()
            elif test == "fulfill_conditions":
                if len(sys.argv) < 3:
                    print("Usage: python3 scripts/interact.py fulfill_conditions idx1 idx2")
                    sys.exit(1)
                #parse indices from remaining command-line args (as integers)
                indices = [int(arg) for arg in sys.argv[2:]]
                fulfill_conditions(indices)
            elif test == "check_conditions":
                all_conditions_fulfilled()
            elif test == 'deposit':
                run_deposit()
            elif test == 'release':
                run_release()
            elif test == "incomplete_and_refund":
                run_incomplete_and_refund()
            
            # NEW: ConditionVerifier commands
            elif test == 'deposit_to_verifier':
                deposit_to_verifier()
            
            elif test == 'verify_external_condition':
                verify_external_condition()
            
            elif test == 'get_external_condition_details':
                get_external_condition_details()
            
            elif test == 'escrow_summary':
                print_escrow_summary()
            else:
                print(f"Unknown test case: {test}. *Note: just ignore this if you see an output when calling one of the non-main functions")
                print("\nAvailable commands:") # Added list of available commands
                print("  deposit, add_conditions, print_all_conditions, fulfill_conditions")
                print("  check_conditions, release, incomplete_and_refund")
                print("  deposit_to_verifier, verify_external_condition")
                print("  get_condition_details, escrow_summary")

    # Print comprehensive audit trail 
    print("\n=== Full Audit Trail ===")
    for step in audit_trail:
        print(f"\nScenario: {step['step']}")
        print(f"TX Hash: {step['tx_hash']}")
        print(f"State: {step['state']['state']}")
        print(f"Buyer Balance: {step['state']['buyer_balance']}")
        print(f"Seller Balance: {step['state']['seller_balance']}")
        print(f"Contract Balance: {step['state']['contract_balance']}")
        print(f"Amount Locked: {step['state']['amount_locked']}")
        print(f"Events: {step.get('events', [])}")
        print(f"Status: {step.get('status')}")
        if 'message' in step: print(f"Message: {step['message']}")
        print("------------------------------------------------")
