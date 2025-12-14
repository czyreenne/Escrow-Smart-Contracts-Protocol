import os, sys, json
from web3 import Web3
from datetime import datetime, timezone

NETWORK_NAME = "ganache"
CONTRACT_NAME = "Escrow"

def deploy_condition_verifier():
    # Deploy ConditionVerifier contract
    deployer_private_key = os.environ.get('DEPLOYER_PRIVATE_KEY')
    if not deployer_private_key:
        raise Exception("DEPLOYER_PRIVATE_KEY not set in environment")
    
    # Load ConditionVerifier ABI and bytecode
    with open('contracts/ConditionVerifier.abi') as f:
        cv_abi = json.load(f)
    with open('contracts/ConditionVerifier.bin') as f:
        cv_bytecode = f.read().strip()
    
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    assert w3.is_connected(), "Web3 not connected to Ganache!"
    
    deployer_account = w3.eth.account.from_key(deployer_private_key)
    deployer_address = deployer_account.address
    
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
    cv_receipt = w3.eth.wait_for_transaction_receipt(cv_tx_hash)
    cv_address = cv_receipt.contractAddress
    
    print(f"ConditionVerifier deployed at: {cv_address}")
    return cv_address, cv_abi, w3


def create_eth_deposit_condition(cv_address, cv_abi, beneficiary_address, required_amount):
    """Create an ETH deposit condition"""
    deployer_private_key = os.environ.get('DEPLOYER_PRIVATE_KEY')
    
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    deployer_account = w3.eth.account.from_key(deployer_private_key)
    deployer_address = deployer_account.address
    
    cv_contract = w3.eth.contract(address=cv_address, abi=cv_abi)
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
    
    signed_condition_tx = w3.eth.account.sign_transaction(
        create_condition_tx, 
        private_key=deployer_private_key
    )
    condition_tx_hash = w3.eth.send_raw_transaction(signed_condition_tx.raw_transaction)
    condition_receipt = w3.eth.wait_for_transaction_receipt(condition_tx_hash)
    
    # Get condition_id from event
    condition_created_event = cv_contract.events.ConditionCreated().process_receipt(condition_receipt)
    condition_id = condition_created_event[0]['args']['condition_id']
    
    print(f"Condition created with ID: {condition_id}")
    return condition_id


def deploy_escrow_with_verifier(seller_address, timeout, beneficiary_address, required_amount):
    """
    Deploy full escrow system: ConditionVerifier + Condition + Escrow
    
    Returns: (escrow_address, escrow_abi, cv_address, cv_abi, condition_id, w3)
    """
    deployer_private_key = os.environ.get('DEPLOYER_PRIVATE_KEY')
    if not deployer_private_key:
        raise Exception("DEPLOYER_PRIVATE_KEY not set in environment")
    
    # Step 1: Deploy ConditionVerifier
    cv_address, cv_abi, w3 = deploy_condition_verifier()
    
    # Step 2: Create ETH deposit condition
    condition_id = create_eth_deposit_condition(cv_address, cv_abi, beneficiary_address, required_amount)
    
    # Step 3: Deploy Escrow
    with open('contracts/Escrow.abi') as f:
        escrow_abi = json.load(f)
    with open('contracts/Escrow.bin') as f:
        escrow_bytecode = f.read().strip()
    
    deployer_account = w3.eth.account.from_key(deployer_private_key)
    deployer_address = deployer_account.address
    
    Escrow = w3.eth.contract(abi=escrow_abi, bytecode=escrow_bytecode)
    nonce = w3.eth.get_transaction_count(deployer_address)
    
    escrow_tx = Escrow.constructor(
        seller_address,
        timeout,
        cv_address,
        condition_id,
        beneficiary_address
    ).build_transaction({
        "from": deployer_address,
        "nonce": nonce,
        "gas": 4000000,
        "gasPrice": w3.to_wei("20", "gwei"),
    })
    
    signed_escrow_tx = w3.eth.account.sign_transaction(escrow_tx, private_key=deployer_private_key)
    escrow_tx_hash = w3.eth.send_raw_transaction(signed_escrow_tx.raw_transaction)
    escrow_receipt = w3.eth.wait_for_transaction_receipt(escrow_tx_hash)
    escrow_address = escrow_receipt.contractAddress
    
    print(f"Escrow deployed at: {escrow_address}")
    
    return escrow_address, escrow_abi, cv_address, cv_abi, condition_id, w3


# Backward compatibility: Deploy escrow without verifier (for migration)
def deploy_escrow_simple(seller_address, timeout):
    """
    DEPRECATED: Old-style deployment (won't work with current Escrow.vy)
    Use deploy_escrow_with_verifier() instead
    """
    raise NotImplementedError(
        "Simple deployment no longer supported. "
        "Use deploy_escrow_with_verifier() instead."
    )


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python scripts/test_deploy.py <seller> <timeout> <beneficiary> <required_amount>")
        sys.exit(1)
    
    seller_address = sys.argv[1]
    timeout = int(sys.argv[2])
    beneficiary_address = sys.argv[3]
    required_amount = int(sys.argv[4])
    
    escrow_address, escrow_abi, cv_address, cv_abi, condition_id, w3 = deploy_escrow_with_verifier(
        seller_address, 
        timeout, 
        beneficiary_address, 
        required_amount
    )
    
    print("\n=== Deployment Summary ===")
    print(f"ConditionVerifier: {cv_address}")
    print(f"Condition ID: {condition_id}")
    print(f"Escrow: {escrow_address}")
