import os, sys, json
from web3 import Web3
from web3.exceptions import ContractLogicError
from datetime import datetime
from test_deploy import deploy_escrow_contract
import random

# Set up audit trail collector 
audit_trail = []

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
assert w3.is_connected(), "Web3 connection failed!"
buyer_priv = os.environ.get("BUYER_PRIVATE_KEY")
seller_priv = os.environ.get("SELLER_PRIVATE_KEY")
buyer = w3.eth.account.from_key(buyer_priv)
seller = w3.eth.account.from_key(seller_priv)

def fuzz_iteration(): 
    contract_address, escrow_abi = deploy_escrow_contract(seller.address, random.randint(10,5000))
    escrow = w3.eth.contract(address=contract_address, abi = escrow_abi)
    try:
        value = w3.to_wei(random.uniform(0.000001,10), 'ether')
        deposit_tx = escrow.functions.deposit().build_transaction({
            "from":buyer.address,
            "value": value,
            "nonce": w3.eth.get_transaction_count(buyer.address),
            "gas": 200000,
            "gasPrice": w3.to_wei("20", "gwei")
        })
        signed_deposit = w3.eth.account.sign_transaction(deposit_tx, buyer_priv)
        w3.eth.send_raw_transaction(signed_deposit.raw_transaction)
        print(f"Deposit of {value} succeeded!")
    except Exception as e:
        print(f"Deposit error: {e}")

    # Randomly add between 0 and 10 conditions, some with odd data
    num_conditions = random.randint(0, 10)
    for i in range(num_conditions):
        desc = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=random.randint(0, 100)))
        try:
            add_tx = escrow.functions.add_conditions(desc).build_transaction({
                "from": buyer.address,
                "nonce": w3.eth.get_transaction_count(buyer.address),
                "gas": 2000000,
                "gasPrice": w3.to_wei("20", "gwei"),
            })
            signed_add = w3.eth.account.sign_transaction(add_tx, buyer_priv)
            w3.eth.send_raw_transaction(signed_add.raw_transaction)
            print(f"Condition of: {desc} added!")
        except Exception as e:
            print(f"Could not add condition of {desc}: {e}")
    
    # Randomly fulfill conditions, some out of bound
    for i in range(random.randint(0, num_conditions+3)):
        try:
            tx = escrow.functions.fulfill_condition(i).build_transaction({
                "from": seller.address,
                "nonce": w3.eth.get_transaction_count(seller.address),
                "gas": 100000,
                "gasPrice": w3.to_wei("200", "gwei")
            })
            signed_fulfill = w3.eth.account.sign_transaction(tx, seller_priv)
            w3.eth.send_raw_transaction(signed_fulfill.raw_transaction)
            print(f"Condition {i} fulfilled.")
        except Exception as e:
            print(f"Error fulfilling condition {i}: {e}")
    
    for _ in range(random.randint(1, 3)):
        action = random.choice(['release', 'refund'])
        try:
            if action == 'release':
                release_tx = escrow.functions.release().build_transaction({
                    "from": seller.address,
                    "nonce": w3.eth.get_transaction_count(seller.address),
                    "gas": 200000,
                    "gasPrice": w3.to_wei("20", "gwei")
                })
                signed_release = w3.eth.account.sign_transaction(release_tx, seller_priv)
                tx_hash_release = w3.eth.send_raw_transaction(signed_release.raw_transaction)
                rcpt_release = w3.eth.wait_for_transaction_receipt(tx_hash_release)
                if rcpt_release.status:
                    print("Release succeeded!")
                else:
                    print("Release failed.")
            else:
                w3.provider.make_request("evm_increaseTime", [3600])
                w3.provider.make_request("evm_mine", [])
                refund_tx = escrow.functions.refund().build_transaction({
                    "from": buyer.address,
                    "nonce": w3.eth.get_transaction_count(buyer.address),
                    "gas": 200000,
                    "gasPrice": w3.to_wei("20", "gwei")
                })
                signed_refund = w3.eth.account.sign_transaction(refund_tx, buyer_priv)
                tx_hash_refund = w3.eth.send_raw_transaction(signed_refund.raw_transaction)
                rcpt_refund = w3.eth.wait_for_transaction_receipt(tx_hash_refund)
                if rcpt_refund.status== 1:
                    print("Refund succeeded!")
                else:
                    print("Refund failed.")
        except Exception as e:
            print(f"{action.capitalize()} error: {e}")

for i in range(100):
    print(f"=== Fuzz iteration {i} ===")
    fuzz_iteration()