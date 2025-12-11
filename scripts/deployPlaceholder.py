# python scripts/deploy.py <seller_address> <timeout> <beneficiary_address> <required_eth_amount_in_wei>

import os
import sys
import json
from web3 import Web3
from datetime import datetime, timezone
import getpass

# Ensures that only buyer/deployer can run the script
private_key = getpass.getpass(prompt="Enter deployer private key: ")
os.environ['DEPLOYER_PRIVATE_KEY'] = private_key
DEPLOYER_PRIVATE_KEY = os.environ.get("DEPLOYER_PRIVATE_KEY")
assert DEPLOYER_PRIVATE_KEY is not None, "ERROR: Deployer private key must be set in environment!"

# Calculate deployer address securely from private key
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
deployer_account = w3.eth.account.from_key(DEPLOYER_PRIVATE_KEY)
deployer_address = deployer_account.address.lower().strip()
print(f"Deployer address: {deployer_address}")

# Check address against a whitelist
EXPECTED_ADDRESSES = [
    os.environ.get("DEPLOYER_ADDRESS", "").lower(),
]

assert deployer_address in EXPECTED_ADDRESSES, (
    "ERROR: Private key does not match any authorized deployer address."
)

print("Verified: deployment authorized for address", deployer_address)

# Network configuration
NETWORK_NAME = "ganache"

# Check command-line arguments
if len(sys.argv) < 5:
    print("Usage: python scripts/deploy.py <seller_address> <timeout> <beneficiary_address> <required_eth_amount_in_wei>")
    print("Example: python scripts/deploy.py 0x123... 3600 0x456... 1000000000000000000")
    sys.exit(1)

seller_address = sys.argv[1]
timeout = int(sys.argv[2])
beneficiary_address = sys.argv[3]
required_amount = int(sys.argv[4])  # In Wei

# Validate addresses
assert w3.is_address(seller_address), "Invalid seller address"
assert w3.is_address(beneficiary_address), "Invalid beneficiary address"

deployer_private_key = os.environ.get('DEPLOYER_PRIVATE_KEY')
if not deployer_private_key:
    raise Exception("DEPLOYER_PRIVATE_KEY not set in environment")

# ===== STEP 1: Deploy ConditionVerifier =====
print("\n=== Step 1: Deploying ConditionVerifier ===")

# Load ConditionVerifier ABI and bytecode
with open('contracts/ConditionVerifier.abi') as f:
    cv_abi = json.load(f)

with open('contracts/ConditionVerifier.bin') as f:
    cv_bytecode = f.read().strip()

# Connect to Ganache
assert w3.is_connected(), "Web3 not connected to Ganache!"

deployer_account = w3.eth.account.from_key(deployer_private_key)
deployer_address = deployer_account.address

# Deploy ConditionVerifier
ConditionVerifier = w3.eth.contract(abi=cv_abi, bytecode=cv_bytecode)
nonce = w3.eth.get_transaction_count(deployer_address)

cv_tx = ConditionVerifier.constructor().build_transaction({
    "from": deployer_address,
    "nonce": nonce,
    "gas": 4000000,
    "gasPrice": w3.to_wei("20", "gwei"),
})

signed_cv_tx = w3.eth.account.sign_transaction(cv_tx, private_key=deployer_private_key)
cv_tx_hash = w3.eth.send_raw_transaction(signed_cv_tx.raw_transaction)
print(f"ConditionVerifier deployment TX hash: {cv_tx_hash.hex()}")

cv_receipt = w3.eth.wait_for_transaction_receipt(cv_tx_hash)
cv_address = cv_receipt.contractAddress
print(f"ConditionVerifier deployed at: {cv_address}")

# ===== STEP 2: Create ETH deposit condition =====
print("\n=== Step 2: Creating ETH deposit condition ===")

# Attach to deployed ConditionVerifier
cv_contract = w3.eth.contract(address=cv_address, abi=cv_abi)

# Create condition (seller calls this)
nonce = w3.eth.get_transaction_count(deployer_address)

create_condition_tx = cv_contract.functions.create_eth_deposit_condition(
    beneficiary_address,
    required_amount
).build_transaction({
    "from": deployer_address,
    "nonce": nonce,
    "gas": 500000,
    "gasPrice": w3.to_wei("20", "gwei"),
})

signed_condition_tx = w3.eth.account.sign_transaction(create_condition_tx, private_key=deployer_private_key)
condition_tx_hash = w3.eth.send_raw_transaction(signed_condition_tx.raw_transaction)
print(f"Create condition TX hash: {condition_tx_hash.hex()}")

condition_receipt = w3.eth.wait_for_transaction_receipt(condition_tx_hash)

# Get the condition_id from the transaction receipt (from ConditionCreated event)
condition_created_event = cv_contract.events.ConditionCreated().process_receipt(condition_receipt)
condition_id = condition_created_event[0]['args']['condition_id']
print(f"Condition created with ID: {condition_id}")

# ===== STEP 3: Deploy Escrow =====
print("\n=== Step 3: Deploying Escrow ===")

# Load Escrow ABI and bytecode
with open('contracts/Escrow.abi') as f:
    escrow_abi = json.load(f)

with open('contracts/Escrow.bin') as f:
    escrow_bytecode = f.read().strip()

Escrow = w3.eth.contract(abi=escrow_abi, bytecode=escrow_bytecode)
nonce = w3.eth.get_transaction_count(deployer_address)

escrow_tx = Escrow.constructor(
    seller_address,
    timeout,
    cv_address,  # ConditionVerifier address
    condition_id,  # External condition ID
    beneficiary_address
).build_transaction({
    "from": deployer_address,
    "nonce": nonce,
    "gas": 4000000,
    "gasPrice": w3.to_wei("20", "gwei"),
})

signed_escrow_tx = w3.eth.account.sign_transaction(escrow_tx, private_key=deployer_private_key)
escrow_tx_hash = w3.eth.send_raw_transaction(signed_escrow_tx.raw_transaction)
print(f"Escrow deployment TX hash: {escrow_tx_hash.hex()}")

escrow_receipt = w3.eth.wait_for_transaction_receipt(escrow_tx_hash)
escrow_address = escrow_receipt.contractAddress
print(f"Escrow deployed at: {escrow_address}")

# ===== STEP 4: Save deployment records =====
print("\n=== Step 4: Saving deployment records ===")

data = {}
json_path = "deployments/testnet.json"

if os.path.exists(json_path):
    with open(json_path, "r") as fjson:
        try:
            data = json.load(fjson)
        except json.JSONDecodeError:
            data = {}

if "deployments" not in data:
    data["network"] = NETWORK_NAME
    data["deployments"] = []

timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# Record ConditionVerifier deployment
cv_record = {
    "contract": "ConditionVerifier",
    "address": cv_address,
    "txHash": cv_tx_hash.hex(),
    "deployer": deployer_address,
    "timestamp": timestamp,
    "constructorArgs": []
}

# Record Escrow deployment
escrow_record = {
    "contract": "Escrow",
    "address": escrow_address,
    "txHash": escrow_tx_hash.hex(),
    "deployer": deployer_address,
    "seller": seller_address,
    "timestamp": timestamp,
    "constructorArgs": [seller_address, timeout, cv_address, condition_id, beneficiary_address],
    "linkedContracts": {
        "conditionVerifier": cv_address,
        "externalConditionId": condition_id,
        "beneficiary": beneficiary_address,
        "requiredAmount": required_amount
    }
}

data["deployments"].append(cv_record)
data["deployments"].append(escrow_record)

with open(json_path, "w") as fout:
    json.dump(data, fout, indent=2)

print("Deployment recorded in testnet.json")

print("\n=== Deployment Summary ===")
print(f"ConditionVerifier: {cv_address}")
print(f"Condition ID: {condition_id}")
print(f"Escrow: {escrow_address}")
print(f"Seller: {seller_address}")
print(f"Beneficiary: {beneficiary_address}")
print(f"Required amount: {required_amount} Wei ({w3.from_wei(required_amount, 'ether')} ETH)")
print(f"Timeout: {timeout} seconds")
