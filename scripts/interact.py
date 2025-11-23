# Below are various interactions with the deployed contract for the purposes of the demo

import os
import json
from web3 import Web3
from datetime import datetime
import sys

# Set up audit trail collector 
audit_trail = []

# Load deployment info from testnet.json 
with open("deployments/testnet.json") as f:
    data = json.load(f)
contract_info = data["deployments"][-1]  # Use latest deployment

contract_address = contract_info["address"]

# Load ABI 
with open('contracts/Escrow.abi') as f:
    escrow_abi = json.load(f)

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
escrow = w3.eth.contract(address=contract_address, abi=escrow_abi)

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
        'contract_balance': w3.eth.get_balance(contract_address),
        'amount_locked': escrow.functions.amount().call()
    }

def print_state(state_dict):
    print("\n Current Contract State")
    print(f"State  (0=Init, 1=Funded, 2=Released, 3=Refunded): {state_dict['state']}")
    print(f"Buyer:   {state_dict['buyer']} | Balance: {state_dict['buyer_balance']}")
    print(f"Seller:  {state_dict['seller']} | Balance: {state_dict['seller_balance']}")
    print(f"Contract balance: {state_dict['contract_balance']}")
    print(f"Amount locked: {state_dict['amount_locked']}\n")

def get_events(event_name, tx_hash):
    # This pulls event logs for a tx in a normalized format
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    events = getattr(escrow.events, event_name)().process_receipt(receipt)
    return [dict(e.args) for e in events]

# 1. Deposit by Buyer 
def run_deposit():
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

# 2. Seller releases funds (claim) 
def run_release():
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

# 3. Refund scenarios

# A. Refund before release
def run_refund_before_release():
    print("\n=== Refund Before Release (Should Succeed) ===")

    # Deposit funds
    deposit_tx = escrow.functions.deposit().build_transaction({
        "from": buyer.address,
        "value": w3.to_wei("1", "ether"),
        "nonce": w3.eth.get_transaction_count(buyer.address),
        "gas": 200000,
        "gasPrice": w3.to_wei("20", "gwei")
    })
    signed_deposit = w3.eth.account.sign_transaction(deposit_tx, buyer_priv)
    tx_hash_deposit = w3.eth.send_raw_transaction(signed_deposit.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash_deposit)
    state_dict = get_state()
    print_state(state_dict)

    # Fast-forward time past timeout
    w3.provider.make_request("evm_increaseTime", [3601])
    w3.provider.make_request("evm_mine", [])

    # Try refund (should work)
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
        result = "Refund succeeded (as expected, before release and after timeout)" if rcpt_refund.status == 1 else "Refund failed unexpectedly."
        print(result)
        audit_trail.append({
            "step": "refund_before_release",
            "tx_hash": tx_hash_refund.hex(),
            "state": state_after,
            "status": rcpt_refund.status,
            "events": get_events("Refunded", tx_hash_refund),
            "message": result
        })
    except Exception as e:
        print(f"Refund attempt before release failed: {e}")
        audit_trail.append({
            "step": "refund_before_release",
            "tx_hash": None,
            "state": get_state(),
            "status": 0,
            "events": [],
            "message": str(e)
        })

if __name__ == "__main__":
    # Usage: `python scripts/interact.py NAME_OF_STEP`
    #     python interact.py deposit           # (just runs deposit)
    #     or python interact.py deposit release   # (runs both)
    #     or python interact.py all               # (runs all steps in order)

    # The Escrow contract `state` field means:
    #   0 = Init      (Contract is freshly deployed, no funds yet)
    #   1 = Funded    (Buyer has deposited funds, waiting for release or refund)
    #   2 = Released  (Seller has claimed the funds)
    #   3 = Refunded  (Funds returned to buyer after timeout)

    # The transaction `status` field means:
    #   1 = Success   (Transaction executed and state changed as intended)
    #   0 = Failed    (Transaction reverted—an error, assert, or require failed; no state change except gas spent)

    tests_to_run = sys.argv[1:] if len(sys.argv) > 1 else []

    if not tests_to_run or 'all' in tests_to_run:
        run_deposit()
        run_release()
        run_refund_before_release()
    else:
        for test in tests_to_run:
            if test == 'deposit':
                run_deposit()
            elif test == 'release':
                run_release()
            elif test == 'refund_before_release':
                run_refund_before_release()
            else:
                print(f"Unknown test case: {test}")

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
