# Below are various interactions with the deployed contract for the purposes of the demo

import os
import json
from web3 import Web3
from datetime import datetime

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
def print_state():
    print(f"\n Current Contract State")
    print(f"State  (0=Init, 1=Funded, 2=Released, 3=Refunded): {escrow.functions.state().call()}")
    print(f"Buyer:   {escrow.functions.buyer().call()} | Balance: {w3.eth.get_balance(escrow.functions.buyer().call())}")
    print(f"Seller:  {escrow.functions.seller().call()} | Balance: {w3.eth.get_balance(escrow.functions.seller().call())}")
    print(f"Contract balance: {w3.eth.get_balance(contract_address)}")
    print(f"Amount locked: {escrow.functions.amount().call()}")
    print("")

def get_events(event_name, tx_hash):
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    events = getattr(escrow.events, event_name)().process_receipt(receipt)
    return [dict(e.args) for e in events]

# Step 1. Deposit by Buyer 
print("Step 1: Buyer deposits to escrow\n")
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
print(f"Deposit TX hash: {tx_hash_deposit.hex()}")

print_state()

print("Checking for Deposited event...")
deposited_events = get_events("Deposited", tx_hash_deposit)
print(deposited_events)

# Step 2. Seller releases funds (claim) 
print("\nStep 2: Seller releases funds\n")
release_tx = escrow.functions.release().build_transaction({
    "from": seller.address,
    "nonce": w3.eth.get_transaction_count(seller.address),
    "gas": 200000,
    "gasPrice": w3.to_wei("20", "gwei")
})
signed_release = w3.eth.account.sign_transaction(release_tx, seller_priv)
tx_hash_release = w3.eth.send_raw_transaction(signed_release.raw_transaction)
rcpt_release = w3.eth.wait_for_transaction_receipt(tx_hash_release)
print(f"Release TX hash: {tx_hash_release.hex()}")

print_state()

print("Checking for Released event...")
released_events = get_events("Released", tx_hash_release)
print(released_events)

# Step 3. Refund scenario (buyer tries refund *after* release = should fail; so let's redeploy/fund again) 

# TO DEMONSTRATE REFUND LOGIC: For real unit tests, you'd redeploy or reset state
# Here, we can try refund right after release (should fail due to state)

try:
    print("\nStep 3: Buyer tries to refund after release (should fail)")
    refund_tx = escrow.functions.refund().build_transaction({
        "from": buyer.address,
        "nonce": w3.eth.get_transaction_count(buyer.address),
        "gas": 200000,
        "gasPrice": w3.to_wei("20", "gwei")
    })
    signed_refund = w3.eth.account.sign_transaction(refund_tx, buyer_priv)
    tx_hash_refund = w3.eth.send_raw_transaction(signed_refund.raw_transaction)
    rcpt_refund = w3.eth.wait_for_transaction_receipt(tx_hash_refund)
    print_state()
    if rcpt_refund.status == 0:
        print("Refund transaction failed as expected.")
except Exception as e:
    print("Refund failed with error:", str(e))

# (Optional): To test refund properly, redeploy contract or fast-forward time 
# If you fund a fresh contract, then wait for timeout and call refund:
# NOTE: Use Ganache's 'evm_increaseTime' and 'evm_mine' for time control in real tests.

# Transparency: print all events for full audit trail 
print("\n All Events seen in contract receipts")
for event_name, tx_hash in [("Deposited", tx_hash_deposit), ("Released", tx_hash_release)]:
    print(f"{event_name}:", get_events(event_name, tx_hash))

