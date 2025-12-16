import os, sys, json
from web3 import Web3
from web3.exceptions import ContractLogicError
from datetime import datetime
from test_deploy import deploy_escrow_with_verifier                 # Import the new deployment function

# Set up audit trail collector
audit_trail = []

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
assert w3.is_connected(), "Web3 connection failed!"

# --- HELPER FUNCTIONS ---
# Helper function to deploy fresh contracts
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

def decode_revert_reason_raw(revert_data: str) -> str:
    """Decode Vyper assert from real tx reverts"""
    if not revert_data or revert_data == '0x':
        return "generic revert"
    
    try:
        data_bytes = bytes.fromhex(revert_data[2:] if revert_data.startswith('0x') else revert_data)
        if data_bytes[:4] == b'\x08\xc3\x79\xa0':
            offset = int.from_bytes(data_bytes[4:36], 'big')
            length = int.from_bytes(data_bytes[offset:offset+32], 'big')
            message = data_bytes[offset+32:offset+32+length].decode('utf-8')
            return f"🛑 VYPER ASSERT: '{message}'"
    except:
        pass
    
    return f"raw revert: {revert_data[:50]}..."

def safe_send_tx(tx_fn, from_key, from_addr, value=0, expect_event=None, gas=500000, **kwargs):
    """Send tx + VALIDATE it actually worked"""
    try:
        tx = tx_fn().build_transaction({
            'from': from_addr,
            'value': value,
            'nonce': w3.eth.get_transaction_count(from_addr),
            'gas': gas,
            'gasPrice': w3.to_wei('1', 'gwei'),
            **kwargs
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, from_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 0:
            return False, "TX REVERTED (status=0)"
                
        return True, receipt
        
    except ContractLogicError as ex:
        return False, decode_revert_reason_raw(str(ex))
    except Exception as e:
        return False, str(e)

# --- WORKFLOW FUNCTIONS ---
def deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, amount):
    success, result = safe_send_tx(
        lambda: cv_contract.functions.deposit_eth(condition_id),
        seller_priv, seller.address,
        value=amount,
        gas=500000
    )

    if success:
        print(f"✅ Deposited to ConditionVerifier for condition {condition_id}")
        print("✅ External condition FULFILLED!")
    else:
        print("❌ Deposit to ConditionVerifier FAILED")

# Helper check condition function
def print_all_conditions(contract):
    num = contract.functions.get_num_conditions().call()
    print(f"📋 Total Conditions: {num}")
    for i in range(num):
        desc, fulfilled = contract.functions.get_condition(i).call()
        status = "✅" if fulfilled else "❌"
        print(f"  {status} [{i}] {desc}")

# The basic deposit transaction
def deposit_transaction(contract, buyer, buyer_priv):
    success, result = safe_send_tx(
        contract.functions.deposit,
        buyer_priv, buyer.address,
        value=w3.to_wei("1", "ether"),
        expect_event="Deposited"
    )

    if success:
        print("✅ DEPOSIT SUCCEEDED!")
    else:
        print(f"❌ DEPOSIT FAILED: {result}")

# Basic Add Condition
def add_conditions(contract, buyer, buyer_priv, empty = False):
    if empty == False:
        condition = "Random condition"
    else:
        condition = ""

    success, result = safe_send_tx(
        lambda: contract.functions.add_conditions(condition),
        buyer_priv, buyer.address,
        gas=5000000,
        expect_event="ConditionAdded"
    )
    
    if success:
        print(f"✅ Condition ADDED: '{condition}'")
    else:
        print(f"❌ add_conditions FAILED: {result}")

# Basic release condition
def run_release(contract, seller, seller_priv):
    success, result = safe_send_tx(
        contract.functions.release,
        seller_priv, seller.address,
        expect_event="Released"
    )
    
    if success:
        print("✅ RELEASE SUCCEEDED! 🎉!")
    else:
        print(f"❌ RELEASE FAILED: {result}")
        print("\nInternal Condition Check:", end ="") 
        all_conditions_fulfilled(contract, seller)
    
# Basic refund condition
def run_incomplete_and_refund(fast_forward, contract, buyer, buyer_priv, seller):
    w3.provider.make_request("evm_increaseTime", [fast_forward])
    w3.provider.make_request("evm_mine", [])
    if fast_forward > 3600:
        print("⏩ Time advanced past timeout")
    else:
        print("⏩ Time advanced")

    success, result = safe_send_tx(
        contract.functions.refund,
        buyer_priv, buyer.address,
        expect_event="Refunded"
    )

    if success:
        print("✅ REFUND SUCCEEDED!")
    else:
        print(f"❌ REFUND FAILED: {result}")
        print("\nInternal Condition Check:", end ="") 
        all_conditions_fulfilled(contract, seller)

# Fulfill conditions function
def fulfill_conditions(indices, contract, seller, seller_priv):
    unique_indices = list(dict.fromkeys(indices))
    
    for idx in unique_indices:
        success, result = safe_send_tx(
            lambda: contract.functions.fulfill_condition(idx),
            seller_priv, seller.address,
            expect_event="ConditionFulfilled"
        )
        
        if success:
            print(f"✅ Condition {idx} FULFILLED ✓")
        else:
            print(f"❌ fulfill_condition({idx}) FAILED: {result}")

# Check if all conditions are fulfilled
def all_conditions_fulfilled(contract, seller):
    all_fulfilled = contract.functions.all_conditions_fulfilled().call({
        "from": seller.address
    })
    
    if all_fulfilled:
        print("✅ All conditions are fulfilled")
    else:
        print("❌ Not all conditions are fulfilled.")

# --- CUSTOM FUNCTIONS ---
def deposit_transaction_zero_value(contract, buyer, buyer_priv):
    success, result = safe_send_tx(
        contract.functions.deposit,
        buyer_priv, buyer.address,
        value=0,
        expect_event="Deposited"
    )

    if success:
        print("✅ DEPOSIT SUCCEEDED!")
    else:
        print(f"❌ DEPOSIT FAILED: {result}")

# --- TEST 1: Repeated Deposit ---
# Deposit 1 ETH → Deposit 1 ETH again
def test_repeated_deposit():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n💰 Testing repeated deposit...")
    print("EXPECTED RESULT:❌ FAIL - contract has already been funded.\n")
    
    try:
        print("=== Attempting First Deposit ===")
        deposit_transaction(escrow, buyer, buyer_priv)  # Should succeed
        print("=== Attempting Second Deposit ===")
        deposit_transaction(escrow, buyer, buyer_priv)  # Should fail
    except Exception as e:
        print(e)


# --- TEST 2: Early Release (0 completions) ---
# Deposit → Add condition → Release (no fulfillment)
# External condition is NOT fulfilled - should fail
def test_early_release():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n🏃 Testing early release (0 completions)...")
    print("EXPECTED RESULT:❌ FAIL - internal condition not fulfilled.\n")
    
    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        print("===Attempting to perform early release===")
        run_release(escrow, seller, seller_priv)  # Should fail (internal condition not fulfilled)
    except Exception as e:
        print(e)


# --- TEST 3: Edge Timeout ---
# Deposit → Add condition → Fast-forward → Refund
def test_edge_timeout():
    print("---TEST 3A: Edge Timeout---")
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n⏱️ Testing edge timeout: Before Timeout...")
    print("EXPECTED RESULT:❌ FAIL - not enough time has passed to request a refund.\n")
    
    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        print("===Fastforwarding and attempting refund by 3599 (current timeout: 3600)===")
        run_incomplete_and_refund(3599, escrow, buyer, buyer_priv, seller)  # This should fail
    except Exception as e:
        print(e)
    
    print()
    print("---TEST 3B: Edge Timeout---")
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n⏱️ Testing edge timeout: Exactly on Timeout...")
    print("EXPECTED RESULT:❌ FAIL - buyer can only request refund AFTER timeout\n")

    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        print("===Fastforwarding and attempting refund by 3600===")
        run_incomplete_and_refund(3600, escrow, buyer, buyer_priv, seller)  # This should fail also
    except Exception as e:
        print(e)
    
    print()
    print("---TEST 3C: Edge Timeout---")
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n⏱️ Testing edge timeout: Just after timeout...")
    print("EXPECTED RESULT:✅ SUCCESS - enough time has passed\n")
    
    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        print("===Fastforwarding and attempting refund by just over 3600===")
        run_incomplete_and_refund(3601, escrow, buyer, buyer_priv, seller)  # This should succeed
    except Exception as e:
        print(e)


# --- TEST 4: Refund After Completion ---
# Deposit → Add condition → Fulfill → Fast-forward → Refund
def test_refund_after_completion():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n🔙 Testing Refund after Completing All Conditions...")
    print("EXPECTED RESULT:❌ FAIL - buyer cannot request refund after seller has completed conditions\n")

    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Completing Condition===")
        fulfill_conditions([0], escrow, seller, seller_priv)
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        print("===Fastforwarding and attempting refund by just over 3600===")
        run_incomplete_and_refund(3601, escrow, buyer, buyer_priv, seller)  # This should fail
    except Exception as e:
        print(e)


# --- TEST 5: Invalid Condition Index + Max Conditions Test + Double Completion ---
# Deposit → Add 11 conditions → Fulfill invalid index (10 -> 10 spaces filled, index 0-9)
# Then: Fulfill all 0-9 → Fulfill external condition → Release
# Then: Fulfill 0 again (double fulfill)
def test_invalid_index():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n☝️ Testing Invalid Condition Index + Max Conditions + Double Completion")
    print("This first part tests if we can add an 11th condition and complete it.")
    print("EXPECTED RESULT:❌ FAIL - maximum 10 internal conditions\n")
    try:
        print("===Attempting Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print()

        for i in range(11):
            print(f"===Attempting to add condition {i}===")
            add_conditions(escrow, buyer, buyer_priv)
        
        print("\n===Completing Condition outside of Index===")
        fulfill_conditions([10], escrow, seller, seller_priv)
        print("===Checking conditions===")
        print_all_conditions(escrow)
    except Exception as e:
        print(e)
    
    print("\n📝 This second part now tests if we can fulfill all 10 internal conditions and release funds.")
    print("EXPECTED RESULT:✅ SUCCESS - fulfilling all conditions should allow release.\n")

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
    
    print("\n🤔 This third part tests what happens if we attempt to fulfill the same condition twice")
    print("EXPECTED RESULT:❌ FAIL - Condition has already been fulfilled.\n")
    
    try:
        print("===Completing the first Condition again===")
        fulfill_conditions([0], escrow, seller, seller_priv)  # This correctly results in an error.
    except Exception as e:
        print(e)


# --- TEST 6: Partial Completion Release ---
# Add 2 conditions → Fulfill 1 → Release (should fail)
def test_partial_completion_release():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n🏃 Testing Release while fulfilling only some Conditions...")
    print("EXPECTED RESULT:❌ FAIL - cannot release funds with partial completion.\n")

    try:
        print("===Attempting Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        for i in range(2):
            print(f"===Attempting to add condition {i}===")
            add_conditions(escrow, buyer, buyer_priv)
        print("\n===Completing First Condition===")
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
    print("---TEST 7A: Zero Internal Conditions Release---")
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n0️⃣ Testing Release with 0 internal conditions...")
    print("EXPECTED RESULT:✅ SUCCESS - once the external condition is fulfilled, it should release.\n")

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
    
    print("\n---TEST 7B: Zero Internal Conditions Refund---")
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n0️⃣ Testing Refund with 0 internal conditions...")
    print("EXPECTED RESULT:❌ FAIL - once the external condition is fulfilled, refund is no longer permitted.\n")
    try:
        print("===Attempting Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)

        # Fulfill external condition
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))

        print("===Attempting Refund===")
        run_incomplete_and_refund(3601, escrow, buyer, buyer_priv, seller) # Should work
    except Exception as e:
        print(e)


# --- TEST 8: Empty Description ---
# Add condition with "" (empty string)
def test_empty_description():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n☁️ Testing adding internal condition with empty description...")
    print("EXPECTED RESULT:✅ SUCCESS - no restriction on condition description.\n")

    try:
        print("===Adding Condition with no Description===")
        add_conditions(escrow, buyer, buyer_priv, empty = True)
        print("===Checking Conditions===")
        print_all_conditions(escrow)
    except Exception as e:
        print(e)

# --- TEST 9: Deposit non-buyer ---
def test_deposit_non_buyer():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\n💰 Testing deposit as non-buyer (seller)...")
    print("EXPECTED RESULT:❌ FAIL - only buyer can fund.\n")
    
    try:
        print("=== Attempting Deposit as Seller===")
        deposit_transaction(escrow, seller, seller_priv)  # Should fail
    except Exception as e:
        print(e)

# --- TEST 10: Deposit non-buyer ---
def test_deposit_non_buyer():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting deposit as non-buyer (seller)...")
    print("EXPECTED RESULT:❌ FAIL - only buyer can fund.\n")
    
    try:
        print("=== Attempting Deposit as Seller===")
        deposit_transaction(escrow, seller, seller_priv)
    except Exception as e:
        print(e)

# --- TEST 11: Add Condition non-buyer ---
def test_add_non_buyer():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting add_condition as non-buyer (seller)...")
    print("EXPECTED RESULT:❌ FAIL - only buyer can add conditions.\n")
    
    try:
        print("=== Attempting Add condition as Seller===")
        add_conditions(escrow, seller, seller_priv)
    except Exception as e:
        print(e)

# --- TEST 11: Fulfill Condition non-seller ---
def test_fulfill_non_seller():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting fulfill_conditions as non-seller (buyer)...")
    print("EXPECTED RESULT:❌ FAIL - only seller can fulfill internal conditions.\n")
    
    try:
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Completing Condition as buyer===")
        fulfill_conditions([0], escrow, buyer, buyer_priv)
    except Exception as e:
        print(e)

# --- TEST 12: Release non-seller ---
def test_release_non_seller():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting release as non-seller (buyer)...")
    print("EXPECTED RESULT:❌ FAIL - only seller can call release.\n")
    
    try:
        print("===Attempting Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Completing Condition===")
        fulfill_conditions([0], escrow, seller, seller_priv)
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        print("===Attempting Release as buyer===")
        run_release(escrow, buyer, buyer_priv)
    except Exception as e:
        print(e)

# --- TEST 13: Refund non-buyer ---
def test_refund_non_buyer():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting refund as non-buyer (seller)...")
    print("EXPECTED RESULT:❌ FAIL - only buyer can request refund.\n")
    
    try:
        print("===Attempting Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        print("===Attempting Refund as seller===")
        run_incomplete_and_refund(3601, escrow, seller, seller_priv, seller)
    except Exception as e:
        print(e)

# --- TEST 14: Deposit Zero Value ---
def test_deposit_zero_value():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting deposit with no value...")
    print("EXPECTED RESULT:❌ FAIL - cannot deposit zero value.\n")
    
    try:
        print("=== Attempting Deposit with zero value===")
        deposit_transaction_zero_value(escrow, buyer, buyer_priv)  # Should fail
    except Exception as e:
        print(e)

# --- TEST 15: Release before Deposit ---
def test_release_before_deposit():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting release on non-funded contract...")
    print("EXPECTED RESULT:❌ FAIL - contract has not been funded.\n")
    
    try:
        print("=== Attempting Release===")
        run_release(escrow, seller, seller_priv)
    except Exception as e:
        print(e)

# --- TEST 16: Release before completing external condition ---
def test_early_release_external():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting release before completing external condition...")
    print("EXPECTED RESULT:❌ FAIL - both internal and external conditions must be completed.\n")
    
    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Completing Condition===")
        fulfill_conditions([0], escrow, seller, seller_priv)
        print("=== Attempting Release===")
        run_release(escrow, seller, seller_priv)
    except Exception as e:
        print(e)

# --- TEST 17: Refund before Deposit ---
def test_refund_before_deposit():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting refund on non-funded contract...")
    print("EXPECTED RESULT:❌ FAIL - contract has not been funded.\n")
    
    try:
        print("=== Attempting Refund===")
        run_incomplete_and_refund(3601, escrow, buyer, buyer_priv, seller)
    except Exception as e:
        print(e)

# --- TEST 18: Refund when only internal conditions completed ---
def test_refund_only_internal():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting refund before completing external condition...")
    print("EXPECTED RESULT:✅ SUCCESS - refund can be done as long as any condition (internal/external) is incomplete.\n")
    
    try:
        print("===Attempting deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Completing Condition===")
        fulfill_conditions([0], escrow, seller, seller_priv)
        print("=== Attempting Refund===")
        run_incomplete_and_refund(3601, escrow, buyer, buyer_priv, seller)
    except Exception as e:
        print(e)

# --- TEST 18: Refund when only external condition completed ---
def test_refund_only_external():
    escrow, cv_contract, condition_id, buyer, buyer_priv, seller, seller_priv = setup_contract(3600)
    print("\nTesting refund before completing internal condition...")
    print("EXPECTED RESULT:✅ SUCCESS - refund can be done as long as any condition (internal/external) is incomplete.\n")
    
    try:
        print("===Attempting Deposit===")
        deposit_transaction(escrow, buyer, buyer_priv)
        print("===Attempting to add a simple condition===")
        add_conditions(escrow, buyer, buyer_priv)
        print("===Fulfilling external condition===")
        deposit_to_verifier(cv_contract, condition_id, seller, seller_priv, w3.to_wei("1", "ether"))
        print("=== Attempting Refund===")
        run_incomplete_and_refund(3601, escrow, buyer, buyer_priv, seller)
    except Exception as e:
        print(e)

if __name__ == "__main__":    
    print("---TEST 1: Repeated Deposit---")
    test_repeated_deposit()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 2: Release Before Internal Condition Fulfilment---")
    test_early_release()
    print("---------------------------------------------------------------------------------")
    
    # print("---TEST 3: Edge Timeout---")
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
    
    # print("---TEST 7: Zero Internal Condition Release---")
    test_zero_conditions()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 8: Empty Internal Condition Description---")
    test_empty_description()
    print("---------------------------------------------------------------------------------")

    print("\n---PERMISSION BASED TESTS---\n")

    print("---TEST 9: Deposit Non-buyer---")   
    test_deposit_non_buyer()
    print("---------------------------------------------------------------------------------")

    print("---TEST 10: Add condition non-buyer---")
    test_add_non_buyer()
    print("---------------------------------------------------------------------------------")

    print("---TEST 11: Fulfill condition non-seller---")
    test_fulfill_non_seller()
    print("---------------------------------------------------------------------------------")

    print("---TEST 12: Release non-seller---")
    test_release_non_seller()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 13: Refund non-buyer---")
    test_refund_non_buyer()
    print("---------------------------------------------------------------------------------")

    print("\n---OTHER TESTS---\n")

    print("---TEST 14: Deposit zero value---")
    test_deposit_zero_value()
    print("---------------------------------------------------------------------------------")

    print("---TEST 15: Release before deposit---")
    test_release_before_deposit()
    print("---------------------------------------------------------------------------------")

    print("---TEST 16: Release before completing external condition---")
    test_early_release_external()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 17: Refund before deposit---")
    test_refund_before_deposit()
    print("---------------------------------------------------------------------------------")

    print("---TEST 18: Refund only internal---")
    test_refund_only_internal()
    print("---------------------------------------------------------------------------------")
    
    print("---TEST 19: Refund only external---")
    test_refund_only_external()
    print("---------------------------------------------------------------------------------")

