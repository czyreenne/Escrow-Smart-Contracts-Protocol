import os, sys, json
from web3 import Web3
from web3.exceptions import ContractLogicError
from datetime import datetime
from test_deploy import deploy_escrow_with_verifier                 # Import the new deployment function

# Set up audit trail collector
audit_trail = []

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
assert w3.is_connected(), "Web3 connection failed!"

def setup_contract(timeout, required_amount=1000000000000000000):   # Default 1 ETH
    """
    Setup contract with external condition
    Returns: escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv
    """
    buyer_priv = os.environ.get("BUYER_PRIVATE_KEY")
    seller_priv = os.environ.get("SELLER_PRIVATE_KEY")
    
    if not buyer_priv or not seller_priv:
        raise Exception("BUYER_PRIVATE_KEY and SELLER_PRIVATE_KEY must be set in environment")
    
    buyer = w3.eth.account.from_key(buyer_priv)
    seller = w3.eth.account.from_key(seller_priv)
    
    # Use seller as beneficiary for the external condition
    beneficiary = seller.address
    
    # Deploy full system: ConditionVerifier + Escrow
    escrow_address, escrow_abi, cv_address, cv_abi, condition_id, w3_instance = \
        deploy_escrow_with_verifier(
            seller.address, 
            timeout, 
            beneficiary, 
            required_amount
        )
    
    escrow = w3.eth.contract(address=escrow_address, abi=escrow_abi)
    cv_contract = w3.eth.contract(address=cv_address, abi=cv_abi)
    
    return escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv

# Helper function to deposit to ConditionVerifier (fulfill external condition)
def deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, amount):
    """Deposit to ConditionVerifier to fulfill external condition"""
    deposit_cv_tx = cv_contract.functions.deposit(condition_id).build_transaction({
        "from": seller.address,
        "value": amount,
        "nonce": w3.eth.get_transaction_count(seller.address),
        "gas": 300000,
        "gasPrice": w3.to_wei("20", "gwei")
    })
    
    signed_deposit_cv = w3.eth.account.sign_transaction(deposit_cv_tx, seller_priv)
    tx_hash_deposit_cv = w3.eth.send_raw_transaction(signed_deposit_cv.raw_transaction)
    rcpt_deposit_cv = w3.eth.wait_for_transaction_receipt(tx_hash_deposit_cv)
    
    if rcpt_deposit_cv.status:
        print(f"Deposited to ConditionVerifier for condition {condition_id}")
    else:
        print("Deposit to ConditionVerifier failed")

# Helper check condition function
def print_all_conditions(contract):
    num = contract.functions.get_num_conditions().call()
    print(f"Total Conditions: {num}")
    for i in range(num):
        desc, fulfilled = contract.functions.get_condition(i).call()
        print(f"Condition {i}: {desc} | Fulfilled: {fulfilled}")

# The basic deposit transaction
def deposit_transaction(contract, buyer, buyer_priv):
    deposit_tx = contract.functions.deposit().build_transaction({
        "from": buyer.address,
        "value": w3.to_wei("1", "ether"),  # 1 ETH deposit
        "nonce": w3.eth.get_transaction_count(buyer.address),
        "gas": 200000,
        "gasPrice": w3.to_wei("20", "gwei")
    })
    
    signed_deposit = w3.eth.account.sign_transaction(deposit_tx, buyer_priv)
    tx_hash_deposit = w3.eth.send_raw_transaction(signed_deposit.raw_transaction)
    rcpt_deposit = w3.eth.wait_for_transaction_receipt(tx_hash_deposit)
    
    if rcpt_deposit.status:
        print("Deposit Succeeded!")
    else:
        print("Deposit Failed.")

# Basic Add Condition
def add_conditions(contract, buyer, buyer_priv):
    condition = "Random condition"
    add_tx = contract.functions.add_conditions(condition).build_transaction({
        "from": buyer.address,
        "nonce": w3.eth.get_transaction_count(buyer.address),
        "gas": 2000000,
        "gasPrice": w3.to_wei("20", "gwei"),
    })
    
    signed_add = w3.eth.account.sign_transaction(add_tx, buyer_priv)
    tx_hash_add = w3.eth.send_raw_transaction(signed_add.raw_transaction)
    rcpt_add = w3.eth.wait_for_transaction_receipt(tx_hash_add)
    
    if rcpt_add.status:
        print(f"Condition added: {condition}")
    else:
        print("Condition could not be added.")

# Add Condition with empty description
def add_condition_empty(contract, buyer, buyer_priv):
    condition = ""
    add_tx = contract.functions.add_conditions(condition).build_transaction({
        "from": buyer.address,
        "nonce": w3.eth.get_transaction_count(buyer.address),
        "gas": 2000000,
        "gasPrice": w3.to_wei("20", "gwei"),
    })
    
    signed_add = w3.eth.account.sign_transaction(add_tx, buyer_priv)
    tx_hash_add = w3.eth.send_raw_transaction(signed_add.raw_transaction)
    rcpt_add = w3.eth.wait_for_transaction_receipt(tx_hash_add)
    
    if rcpt_add.status:
        print(f"Condition added: {condition}")
    else:
        print("Condition could not be added.")

# Basic release condition
def run_release(contract, seller, seller_priv):
    release_tx = contract.functions.release().build_transaction({
        "from": seller.address,
        "nonce": w3.eth.get_transaction_count(seller.address),
        "gas": 300000,  # Increased gas for external condition check
        "gasPrice": w3.to_wei("20", "gwei")
    })
    
    signed_release = w3.eth.account.sign_transaction(release_tx, seller_priv)
    tx_hash_release = w3.eth.send_raw_transaction(signed_release.raw_transaction)
    rcpt_release = w3.eth.wait_for_transaction_receipt(tx_hash_release)
    
    if rcpt_release.status:
        print("Release succeeded!")
    else:
        print("Release failed.")

# Basic refund condition
def run_incomplete_and_refund(fast_forward, contract, buyer, buyer_priv):
    w3.provider.make_request("evm_increaseTime", [fast_forward])
    w3.provider.make_request("evm_mine", [])
    
    refund_tx = contract.functions.refund().build_transaction({
        "from": buyer.address,
        "nonce": w3.eth.get_transaction_count(buyer.address),
        "gas": 200000,
        "gasPrice": w3.to_wei("20", "gwei")
    })
    
    signed_refund = w3.eth.account.sign_transaction(refund_tx, buyer_priv)
    tx_hash_refund = w3.eth.send_raw_transaction(signed_refund.raw_transaction)
    rcpt_refund = w3.eth.wait_for_transaction_receipt(tx_hash_refund)
    
    if rcpt_refund.status == 1:
        print("Refund succeeded!")
    else:
        print("Refund failed.")

# Fulfill conditions function
def fulfill_conditions(indices, contract, seller, seller_priv):
    seen = set()
    unique_indices = []
    
    for idx in indices:
        if idx not in seen:
            unique_indices.append(idx)
            seen.add(idx)
    
    for idx2 in unique_indices:
        try:
            tx = contract.functions.fulfill_condition(idx2).build_transaction({
                "from": seller.address,
                "nonce": w3.eth.get_transaction_count(seller.address),
                "gas": 100000,
                "gasPrice": w3.to_wei("200", "gwei")
            })
            
            signed_fulfill = w3.eth.account.sign_transaction(tx, seller_priv)
            tx_hash_fulfill = w3.eth.send_raw_transaction(signed_fulfill.raw_transaction)
            rcpt_fulfill = w3.eth.wait_for_transaction_receipt(tx_hash_fulfill)
            
            if rcpt_fulfill.status:
                print(f" Condition {idx2} fulfilled.")
            else:
                print(f"Error fulfilling condition {idx2}")
        except Exception as e:
            print(e)
    
    print("Condition(s) fulfilled")

# Check if all conditions are fulfilled
def all_conditions_fulfilled(contract, seller):
    all_fulfilled = contract.functions.all_conditions_fulfilled().call({
        "from": seller.address
    })
    
    if all_fulfilled:
        print("All conditions are fulfilled")
    else:
        print("Not all conditions are fulfilled. Please check with print_all_conditions()")


# --- TEST 1: Repeated Deposit ---
# Deposit 1 ETH → Deposit 1 ETH again
def test_repeated_deposit():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("Testing repeated deposit...")
    
    try:
        print("===Attempting First Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)  # Should succeed
        print("===Attempting Second Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)  # Should fail
    except Exception as e:
        print(e)


# --- TEST 2: Early Release (0 completions) ---
# Deposit → Add condition → Release (no fulfillment)
# External condition is NOT fulfilled - should fail
def test_early_release():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("Testing early release (0 completions)...")
    
    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Attempting to perform early release===")
        run_release(escrow, seller, seller_priv)  # Should fail (internal condition not fulfilled)
        print("===Checking conditions===")
        print_all_conditions(escrow)
    except Exception as e:
        print(e)


# --- TEST 3: Edge Timeout ---
# Deposit → Add condition → Fast-forward → Refund
def test_edge_timeout():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("Testing edge timeout: Before Timeout...")
    
    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Fastforwarding and attempting refund by close to 3600===")
        run_incomplete_and_refund(3599, escrow, buyer, buyer_priv)  # This should fail
    except Exception as e:
        print(e)
    
    print()
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting edge timeout: Exactly on Timeout...")
    
    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Fastforwarding and attempting refund by 3600===")
        run_incomplete_and_refund(3600, escrow, buyer, buyer_priv)  # This should fail also
    except Exception as e:
        print(e)
    
    print()
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting edge timeout: Just after timeout...")
    
    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Fastforwarding and attempting refund by just over 3600===")
        run_incomplete_and_refund(3601, escrow, buyer, buyer_priv)  # This should succeed
    except Exception as e:
        print(e)


# --- TEST 4: Refund After Completion ---
# Deposit → Add condition → Fulfill → Fast-forward → Refund
def test_refund_after_completion():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    
    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Completing Condition===")
        fulfill_conditions([0], escrow, seller, seller_priv)
        print("===Fastforwarding and attempting refund by just over 3600===")
        run_incomplete_and_refund(3601, escrow, buyer, buyer_priv)  # This should fail
        all_conditions_fulfilled(escrow, seller)
    except Exception as e:
        print(e)


# --- TEST 5: Invalid Condition Index + Max Conditions Test + Double Completion ---
# Deposit → Add 11 conditions → Fulfill invalid index (10 -> 10 spaces filled, index 0-9)
# Then: Fulfill all 0-9 → Fulfill external condition → Release
# Then: Fulfill 0 again (double fulfill)
def test_invalid_index():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    
    try:
        print("===Attempting Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        
        for i in range(11):
            print(f"===Attempting to add condition {i}===")
            add_conditions(escrow, buyer, buyer_priv)
        
        print("===Completing Condition outside of Index===")
        fulfill_conditions([10], escrow, seller, seller_priv)
        print("===Checking conditions===")
        print_all_conditions(escrow)
    except Exception as e:
        print(e)
    
    print("This second part now tests if it will work if we fulfill all 10 conditions")
    
    try:
        print("===Completing all 10 Conditions===")
        fulfill_conditions([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], escrow, seller, seller_priv)
        
        # Fulfill external condition before release
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        
        print("===Attempting Release===")
        run_release(escrow, seller, seller_priv)
        print("===Checking conditions===")
        print_all_conditions(escrow)
    except Exception as e:
        print(e)
    
    print("This third part tests what happens if we attempt to fulfill the same condition twice")
    
    try:
        print("===Completing the first Condition again===")
        fulfill_conditions([0], escrow, seller, seller_priv)  # This correctly results in an error
    except Exception as e:
        print(e)


# --- TEST 6: Partial Completion Release ---
# Add 2 conditions → Fulfill 1 → Release (should fail)
def test_partial_completion_release():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    
    try:
        print("===Attempting Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        
        for i in range(2):
            print(f"===Attempting to add condition {i}===")
            add_conditions(escrow, buyer, buyer_priv)
        
        print("===Completing Condition===")
        fulfill_conditions([0], escrow, seller, seller_priv)
        
        # Fulfill external condition
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        
        print("===Attempting Early Release===")
        run_release(escrow, seller, seller_priv)  # Should fail - internal condition 1 not fulfilled
        print("===Checking conditions===")
        print_all_conditions(escrow)
    except Exception as e:
        print(e)


# --- TEST 7: Zero Conditions Contract ---
# Deposit → Release (no conditions)
# Deposit → Fast-forward → Refund (no conditions)
def test_zero_conditions():
    print("Testing zero condition release")
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    
    try:
        print("===Attempting Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        
        # Fulfill external condition
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        
        print("===Attempting Release===")
        run_release(escrow, seller, seller_priv)  # Should succeed with external condition fulfilled
    except Exception as e:
        print(e)
    
    print("\nTesting zero condition refund")
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    
    try:
        print("===Attempting Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting Refund===")
        run_incomplete_and_refund(3601, escrow, buyer, buyer_priv)  # Should work
        all_conditions_fulfilled(escrow, seller)
    except Exception as e:
        print(e)


# --- TEST 8: Empty Description ---
# Add condition with "" (empty string)
def test_empty_description():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    
    try:
        print("===Adding Condition with no Description===")
        add_condition_empty(escrow, buyer, buyer_priv)  # Should be allowed
        print("===Checking Conditions===")
        print_all_conditions(escrow)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    print("---TESTS BEGIN NOW---\n")
    
    print("---TEST 1: Repeated Deposit---")
    test_repeated_deposit()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 2: Release Before Internal Condition Fulfilment---")
    test_early_release()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 3: Edge Timeout---")
    test_edge_timeout()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 4: Refund after Condition Completion---")
    test_refund_after_completion()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 5: Invalid Internal Condition Index---")
    test_invalid_index()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 6: Partial Internal Condition Fulfilment Release---")
    test_partial_completion_release()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 7: Zero Internal Condition Release---")
    test_zero_conditions()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 8: Empty Internal Condition Description---")
    test_empty_description()
