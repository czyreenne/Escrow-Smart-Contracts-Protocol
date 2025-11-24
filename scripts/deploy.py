# python scripts/deploy.py <seller_address> <timeout_seconds> <num_conditions>
import os
import sys
import json
from web3 import Web3
from datetime import datetime, timezone
import getpass

# Ensures that only buyer/deployer can run the script
private_key = getpass.getpass(prompt="Enter deployer private key: ")
os.environ['DEPLOYER_PRIVATE_KEY'] = private_key # store inputted private key in the OS environ
DEPLOYER_PRIVATE_KEY = os.environ.get("DEPLOYER_PRIVATE_KEY") # This environment variable stores the deployer's private key
assert DEPLOYER_PRIVATE_KEY is not None, "ERROR: Deployer private key must be set in environment!"

# Calculate deployer address securely from private key
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
deployer_account = w3.eth.account.from_key(DEPLOYER_PRIVATE_KEY)
deployer_address = deployer_account.address.lower().strip()
print(deployer_address)

# Check address against a whitelist (could be deployer or buyer, passed via env)
EXPECTED_ADDRESSES = [
    os.environ.get("DEPLOYER_ADDRESS", "").lower(),
]

assert deployer_address in EXPECTED_ADDRESSES, (
    "ERROR: Private key does not match any authorized deployer address."
)

# Use the deployer_account for all transactions below this line.
print("Verified: deployment authorized for address", deployer_address)

# This is the blockchain network name
NETWORK_NAME = "ganache"
# This is the name of your contract
CONTRACT_NAME = "Escrow"

# Check if you typed the seller's address, timeout, and num_conditions when you run the script
if len(sys.argv) < 4:
    print("Usage: python scripts/deploy.py <seller_address> <timeout> <num_conditions>")
    sys.exit(1)

# Get the seller's address from what you typed
seller_address = sys.argv[1]
# NEW: Get the timeout from input! (seconds)
timeout = int(sys.argv[2])
# NEW: Get the number of required conditions from input
num_conditions = int(sys.argv[3])

# Get your secret key from the computer's environment (don't share your key)
deployer_private_key = os.environ.get('DEPLOYER_PRIVATE_KEY')
if not deployer_private_key:
    raise Exception("DEPLOYER_PRIVATE_KEY not set in environment")

# Read the contract's ABI from a file. ABI tells us how to talk to the contract.
with open('contracts/Escrow.abi') as f:
    escrow_abi = json.load(f)
# Read the contract's bytecode from a file. Bytecode is the code that gets deployed.
with open('contracts/Escrow.bin') as f:
    escrow_bytecode = f.read().strip()

# Connect to the Ganache blockchain (it runs on your computer)
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
# Make sure Ganache is running and we can talk to it
assert w3.is_connected(), "Web3 not connected to Ganache!"

# Get your deployer address using your secret key
deployer_account = w3.eth.account.from_key(deployer_private_key)
deployer_address = deployer_account.address

# Create a contract object so we can deploy it
Escrow = w3.eth.contract(abi=escrow_abi, bytecode=escrow_bytecode)
# Find out how many times this address sent a transaction (needed to send a new one)
nonce = w3.eth.get_transaction_count(deployer_address)

# Make a "contract deployment" transaction
tx = Escrow.constructor(seller_address, timeout, num_conditions).build_transaction({
    "from": deployer_address,
    "nonce": nonce,
    "gas": 4000000,                # Amount of "fuel" for the computer
    "gasPrice": w3.to_wei("20", "gwei"),  # Price of the "fuel"
})

# Sign the transaction with your secret key (so only you can send it)
signed_tx = w3.eth.account.sign_transaction(tx, private_key=deployer_private_key)
# Send the signed transaction to the blockchain
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"Deployment TX hash: {tx_hash.hex()}")  # Show the transaction hash

# Wait for the blockchain to finish deploying the contract
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
# Get the new contract's address from the receipt
contract_address = tx_receipt.contractAddress
print(f"Contract deployed at: {contract_address}")

# Save the deployment details in a file called 'testnet.json' 
data = {}
json_path = "deployments/testnet.json"
# If the file exists already, load it
if os.path.exists(json_path):
    with open(json_path, "r") as fjson:
        try:
            data = json.load(fjson)
        except json.JSONDecodeError:
            data = {}

# If this is the first deployment, set up the file with network and deployments list
if "deployments" not in data:
    data["network"] = NETWORK_NAME
    data["deployments"] = []

# Make a record of what we just did (address, transaction, etc.)
deployment_record = {
    "contract": CONTRACT_NAME,
    "address": contract_address,
    "txHash": tx_hash.hex(),
    "deployer": deployer_address,
    "seller": seller_address,
    "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "constructorArgs": [seller_address, timeout, num_conditions]   # NEW: include timeout and num_conditions in record
}
# Add the record to the 'deployments' list
data["deployments"].append(deployment_record)

# Write everything back to the file so we don’t forget
with open(json_path, "w") as fout:
    json.dump(data, fout, indent=2)

print("Deployment recorded in testnet.json")  # Say we're done
