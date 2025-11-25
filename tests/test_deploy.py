# python scripts/deploy.py <seller_address> <timeout_seconds>
import os, sys, json
from web3 import Web3
from datetime import datetime, timezone

# This is the blockchain network name
NETWORK_NAME = "ganache"
# This is the name of your contract
CONTRACT_NAME = "Escrow"


def deploy_escrow_contract(seller_address, timeout):
    # Get your secret key from the computer's environment (don't share your key)
    deployer_private_key = os.environ.get('DEPLOYER_PRIVATE_KEY')
    if not deployer_private_key:
        raise Exception("DEPLOYER_PRIVATE_KEY not set in environment")

    # Read the contract's ABI and bytecode
    with open('contracts/Escrow.abi') as f:
        escrow_abi = json.load(f)
    with open('contracts/Escrow.bin') as f:
        escrow_bytecode = f.read().strip()

    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    assert w3.is_connected(), "Web3 not connected to Ganache!"

    # Get your deployer address using your secret key
    deployer_account = w3.eth.account.from_key(deployer_private_key)
    deployer_address = deployer_account.address

    # Create a contract object so we can deploy it
    Escrow = w3.eth.contract(abi=escrow_abi, bytecode=escrow_bytecode)
    # Find out how many times this address sent a transaction (needed to send a new one)
    nonce = w3.eth.get_transaction_count(deployer_address)

    # Make a "contract deployment" transaction
    tx = Escrow.constructor(seller_address, timeout).build_transaction({
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
    return (contract_address, escrow_abi)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/deploy.py <seller_address> <timeout>")
        sys.exit(1)
    seller_address = sys.argv[1]
    timeout = int(sys.argv[2])
    address = deploy_escrow_contract(seller_address, timeout)
    print("Contract deployed at:", address)