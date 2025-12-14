"""
Runs the deposit - fulfilment of conditions - release, for both internal and external conditions.

Usage: scripts/interact.py -> runs all scenarios in sequence

Manually run each step of the full flow in sequence, deposit - fulfilment of conditions - release, for both internal and external conditions:
python scripts/interact.py deposit
python scripts/interact.py add_conditions "Condition 1"
python scripts/interact.py fulfill_conditions 0 1
python scripts/interact.py release
python scripts/interact.py deposit_to_verifier
python scripts/interact.py verify_external_condition
python scripts/interact.py escrow_summary
"""

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
buyer_priv = os.environ.get("BUYER_PRIVATE_KEY") 
print(buyer_priv)     # set these in your env before running script
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
    """Pull Escrow events for a tx; ignore logs from other contracts."""
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    try:
        event_obj = getattr(escrow.events, event_name)()
        events = event_obj.process_receipt(receipt)
        return [dict(e.args) for e in events]
    except MismatchedABI:
        # Receipt had logs from other contracts; safely ignore them
        return []
    except Exception as e:
        print(f"(info) Could not decode {event_name} from this tx: {e}")
        return []

""" Checks for internal conditions """

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

""" Scenarios """

""" For INTERNAL conditions """
# 1. Deposit by Buyer 
def run_deposit():
    try:
        print("Running deposit workflow")
        print("\nDeposit event test: Buyer deposits to escrow\n")

        # Pre-simulate deposit to get revert reason
        try:
            escrow.functions.deposit().call({
                "from": buyer.address,
                "value": w3.to_wei("1", "ether"),
            })
            print("✓ Pre-check passed for deposit()")
        except ContractLogicError as ex:
            state_dict = get_state()
            print_state(state_dict)
            print(f"❌ Deposit pre-check reverted: {ex}")
            return
        except Exception as ex:
            print(f"⚠️ Deposit pre-check error (non-logic): {ex}")
            # You can choose to return or continue; safer to return
            return

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
    except ContractLogicError as ex:
        state_dict = get_state()
        print_state(state_dict)
        print(f"Deposit failed due to contract logic: {ex}")
    except Exception as e:
        state_dict = get_state()
        print_state(state_dict)
        print(f"Deposit attempt failed due to other error: {e}")

# 2. Add internal conditions 
def add_conditions(description):
    print("Running add internal conditions workflow")
    print("\nAdd internal conditions test: Buyer adds internal conditions.\n")
    # Pre-check: simulate add_conditions
    try:
        escrow.functions.add_conditions(description).call({
            "from": buyer.address
        })
        print("✓ Pre-check passed for add_conditions()")
    except ContractLogicError as ex:
        state_dict = get_state()
        print_state(state_dict)
        print(f"❌ add_conditions pre-check reverted: {ex}")
        return
    except Exception as ex:
        print(f"⚠️ add_conditions pre-check error (non-logic): {ex}")
        return

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
    events = get_events("ConditionAdded", tx_hash_add)
    print("Added condition event:", events)
    state_dict = get_state()

# 3. Fulfil specific conditions 
# NEW: Seller can fulfill specific conditions specified by the index in the input array
def fulfill_conditions(indices):
    print("Running fulfill internal conditions workflow")
    print("\nFulfill internal conditions test: Buyer fulfills internal conditions.\n")
    seen = set()
    unique_indices = []
    for idx in indices:
        if idx not in seen:
            unique_indices.append(idx)
            seen.add(idx)

    for idx2 in unique_indices:
        # Pre-check: simulate fulfill_condition(idx2)
        try:
            escrow.functions.fulfill_condition(idx2).call({
                "from": seller.address
            })
            print(f"✓ Pre-check passed for fulfill_condition({idx2})")
        except ContractLogicError as ex:
            print(f"❌ fulfill_condition({idx2}) pre-check reverted: {ex}")
            continue
        except Exception as ex:
            print(f"⚠️ fulfill_condition({idx2}) pre-check error (non-logic): {ex}")
            continue

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
            state_after = get_state()
        except Exception as ex:
            print(f"Error fulfilling condition {idx2}: {ex} ")

    state_dict = get_state()
    print_state(state_dict)
    print("Condition(s) fulfilled")

""" For EXTERNAL conditions """
# NEW: ConditionVerifier Interaction Functions 
# 4. Seller deposits ETH to fulfil external condition, keeperBot automatically verifies fulfilment 
def deposit_to_verifier():
    """
    Seller deposits ETH to ConditionVerifier to fulfill external condition
    """
    try:
        print("Running deposit for external conditions workflow")
        print("\nDeposit to fulfill external conditions test: Buyer deposits to fulfill external conditions.\n")
        print(f"Condition ID: {condition_id}")
        print(f"Required Amount: {w3.from_wei(required_amount, 'ether')} ETH")
        print(f"Beneficiary: {beneficiary}")
       
       # Handle mismatch
        try:
            fulfilled_events = condition_verifier.events.ConditionFulfilled().process_receipt(receipt)
        except MismatchedABI:
            fulfilled_events = []
        except Exception:
            fulfilled_events = []

        # Pre-check: simulate deposit_eth
        try:
            condition_verifier.functions.deposit_eth(condition_id).call({
                "from": seller.address,
                "value": required_amount,
            })
            print("✓ Pre-check passed for deposit_eth()")
        except ContractLogicError as ex:
            print(f"❌ deposit_eth pre-check reverted: {ex}")
            return
        except Exception as ex:
            print(f"⚠️ deposit_eth pre-check error (non-logic): {ex}")
            return

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
            try:
                fulfilled_events = condition_verifier.events.ConditionFulfilled().process_receipt(receipt)
            except Exception:
                fulfilled_events = []
            if fulfilled_events:
                print("✅ External condition automatically fulfilled!")
                print(f"   Event: {fulfilled_events[0]['args']}")
            else:
                print("⚠️  Condition not yet fulfilled (may need more deposits)")
                
            # Print beneficiary confirmation
            try:
                forwarded_events = condition_verifier.events.EthForwarded().process_receipt(receipt)
            except Exception:
                forwarded_events = []
            if forwarded_events:
                print(f"💸 ETH forwarded to beneficiary: {forwarded_events[0]['args']['beneficiary']}")
        else:
            print("❌ Deposit failed")
    except Exception as e:
        print(f"Error depositing to verifier: {e}")

# 5. Manual verification of external condition instead of by keeperBot agent
def verify_external_condition():
    """
    Only for manual triggering of verification for external workflow: Verify that external condition is fulfilled
    """
    try:
        print("Running verification of external condition status workflow")
        print("\nVerification of fulfilment of external condition test: keeperBot agent validates fulfilment of condition\n")
        print(f"Condition ID: {condition_id}")
        
        # Use simple check instead of get_condition_status
        fulfilled = condition_verifier.functions.is_condition_fulfilled(condition_id).call()
        
        print(f"Fulfilled: {fulfilled}")
        
        # Verify for parties (what Escrow contract checks)
        seller_addr = escrow.functions.seller().call()
        buyer_addr = escrow.functions.buyer().call()
        
        verified = condition_verifier.functions.verify_condition_for_parties(
            condition_id,
            buyer_addr,  # the deployer
            beneficiary
        ).call()
        
        print(f"✓ Verified for Escrow parties: {verified}")
        
        if verified:
            print("✅ External condition ready - release() will succeed")
        else:
            print("❌ External condition not met - release() will fail")   
        return verified
        
    except Exception as e:
        print(f"Error depositing to verifier: {e}")
        return False

""" Overall """
# i. Seller releases funds (claim) 
def run_release():
    try:
        print("Running release workflow")
        print("\nRelease event test: Seller releases funds\n")

        # Pre-simulate release
        try:
            escrow.functions.release().call({
                "from": seller.address
            })
            print("✓ Pre-check passed for release()")
        except ContractLogicError as ex:
            state_dict = get_state()
            print_state(state_dict)
            print(f"❌ Release pre-check reverted: {ex}")
            return
        except Exception as ex:
            print(f"⚠️ Release pre-check error (non-logic): {ex}")
            return

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
    except ContractLogicError as ex:
        state_dict = get_state()
        print_state(state_dict)
        print(f"Release failed due to contract logic: {ex}")
    except Exception as e:
        state_dict = get_state()
        print_state(state_dict)
        print(f"Release attempt failed due to other error: {e}")

# ii. Refund: Incomplete fulfillment then refund before release
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
    except ContractLogicError as ex:
        current_state = get_state()
        fulfilled = []
        num_conditions = escrow.functions.get_num_conditions().call()
        for i in range(num_conditions):
            _desc, is_fulfilled = escrow.functions.get_condition(i).call()
            if is_fulfilled:
                fulfilled.append(i)
        print(f"Refund failed due to contract logic: {ex}\nFulfilled conditions at failure: {fulfilled}")
    except Exception as e:
        current_state = get_state()
        print(f"Refund attempt failed due to other error: {e}")

""" Archive """
def get_external_condition_details():
    """Get full details of the external condition"""
    try:
        print("\n⚠️  get_condition_details() temporarily disabled due to flag/enum issue")
        print("Use verify_external_condition() instead")
    except Exception as e:
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
        # run_release()
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
            
            # NEW: ConditionVerifier commands
            elif test == 'deposit_to_verifier':
                deposit_to_verifier()
            
            elif test == 'verify_external_condition':
                verify_external_condition()
            
            elif test == 'get_external_condition_details':
                get_external_condition_details()
            
            # Summaries and Audits
            elif test == 'escrow_summary':
                print_escrow_summary()

            elif test == 'full_audit':
                print_complete_audit_trail(escrow_address)

            else:
                print(f"Unknown test case: {test}. *Note: just ignore this if you see an output when calling one of the non-main functions")
                print("\nAvailable commands:") # Added list of available commands
                print("  deposit, add_conditions, print_all_conditions, fulfill_conditions")
                print("  check_conditions, release")
                print("  deposit_to_verifier, verify_external_condition")
                print("  get_condition_details, escrow_summary")


