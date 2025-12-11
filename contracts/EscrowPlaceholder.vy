# SPDX-License-Identifier: MIT
# @version 0.4.3

# Events act as messages or signals. They help us know what happened inside the contract.
event Deposited:
    buyer: address                          # Who sent the money
    amount: uint256                         # How much money was sent

event Released:
    seller: address                         # Who received money
    amount: uint256                         # How much money was sent

event Refunded:
    buyer: address                          # Who got money back
    amount: uint256                         # How much money was refunded

# track condition status
event ConditionFulfilled:
    index: uint256                          # Index of completed condition
    description: String[100]                # Description of condition completed

# Condition added
event ConditionAdded:
    index: uint256                          # Index of completed condition
    description: String[100]

# Interface to interact with ConditionVerifier contract
interface IConditionVerifier:
    def is_condition_fulfilled(condition_id:uint256) -> bool: view
    def verify_condition_for_parties(
        condition_id: uint256,
        expected_creator: address,
        expected_beneficiary: address
    ) -> bool: view
    def get_condition_status(condition_id: uint256) -> (bool, bool, uint256, uint256): view

# Main Players and Rules 
buyer: public(address)                      # This person pays the seller (gets set when contract starts)
seller: public(address)                     # This person receives money from the buyer
timeout: public(uint256)                    # How long before the buyer can get a refund
start: public(uint256)                      # When the contract started
amount: public(uint256)                     # How much money is in the contract
state: public(uint8)                        # What is happening? 0 = not funded, 1 = funded

# Support for dynamic conditions
struct Condition:
    description: String[100]                # A brief description of the condition
    idx: uint256                            # Index assigned to the condition for ordering
    fulfilled: bool                         # Tracks the fulfilment status of the condition

defaultCondition: public(Condition)
conditions: public(Condition[10])
num_conditions: public(uint256)             # Total conditions required

# External Condition Verification
condition_verifier: public(address)         # Address of ConditionVerifier contract
external_condition_id: public(uint256)      # The condition ID to verify
beneficiary: public(address)                # Third-party beneficiary for external condition

# What happens when the contract is created 
@deploy
def __init__(_seller: address, _timeout: uint256, _condition_verifier: address, _external_condition_id: uint256, _beneficiary: address):
    self.buyer = msg.sender                 # The person starting the contract is the buyer
    self.seller = _seller                   # The seller's address
    self.timeout = _timeout                 # How long before refund is possible
    self.start = block.timestamp            # Remember when we started
    self.state = 0                          # Start in 'not funded' state
    self.condition_verifier = _condition_verifier
    self.external_condition_id = _external_condition_id
    self.beneficiary = _beneficiary

# Buyer puts money in (deposit) 
@payable
@external
def deposit():
    assert self.state == 0, "Contract has already been funded"      # Only if not funded already
    assert msg.sender == self.buyer, "permission denied"            # Only the buyer may deposit
    assert msg.value > 0, "Cannot deposit 0 wei"                    # Must send some money
    self.amount = msg.value                                         # Save how much was sent
    self.state = 1                                                  # Now we are funded
    log Deposited(buyer=msg.sender, amount=msg.value)               # Announce that a deposit happened

# Allows the buyer to add conditions
@external
def add_conditions(desc: String[100]):
    assert msg.sender == self.buyer, "permission denied"
    assert self.num_conditions < 10, "exceeded number of conditions set"
    self.conditions[self.num_conditions].description = desc
    self.conditions[self.num_conditions].idx = self.num_conditions
    self.conditions[self.num_conditions].fulfilled = False
    self.num_conditions += 1                # num_conditions ranges from 1 to 10
    log ConditionAdded(index=self.num_conditions-1, description=self.conditions[self.num_conditions-1].description)

# Normally should be automated but for simplicity's sake we include a function that allows us to set conditions to completed.
# For simplicity's sake: we just let the seller call this.
# In a sense, the condition just becomes: Seller must call fulfill_condition(idx:uint256) function.
@external
def fulfill_condition(idx:uint256):
    '''
    Changelog: removed status=bool >> not necessary, only logs completed transactions
    To add: Access-based controls
    '''
    assert msg.sender == self.seller
    assert idx < self.num_conditions
    assert not self.conditions[idx].fulfilled
    self.conditions[idx].fulfilled = True
    log ConditionFulfilled(index=idx, description=self.conditions[idx].description)

# Check if all conditions are fulfilled. NOTE: restricted by num_conditions not actually checking throughout entire array
@internal
@view
def _all_conditions_fulfilled() -> bool:
    '''
    Made it internal and included an external function to call it below. 
    '''
    for i: uint256 in range(self.num_conditions, bound=10):
        if not self.conditions[i].fulfilled:
            return False
    return True

# NEW: Check external automated condition
@internal
@view
def _check_external_condition() -> bool:
    if self.condition_verifier == empty(address):
        return True # No external condition required
    
    # Use staticcall to query ConditionVerifier
    return staticcall IConditionVerifier(self.condition_verifier).verify_condition_for_parties(
        self.external_condition_id,
        self.seller,
        self.beneficiary
    )

# Seller can check if they have fulfilled all conditions
@external
@view
def all_conditions_fulfilled() -> bool:
    assert msg.sender == self.seller                        # Only seller can check
    return self._all_conditions_fulfilled()

# Check the details of a specific condition
@external
@view
def get_condition(idx: uint256) -> (String[100], bool):
    assert idx < self.num_conditions
    return self.conditions[idx].description, self.conditions[idx].fulfilled

# Check the total number of conditions
@external
@view
def get_num_conditions() -> uint256:
    return self.num_conditions

# Seller can claim money (release) 
@external
def release():
    assert self.state == 1, "contract has not been funded"                                                      # Only if contract is funded 
    assert msg.sender == self.seller, "permission denied"                                                       # Only the seller can claim
    assert self._all_conditions_fulfilled(), "not all conditions have been fulfilled"                           # Only if all conditions fulfilled
    assert self._check_external_condition(), "External condition not fulfilled!"

    # Prevention of REENTRANCY attacks: Change contract state to 'done' BEFORE sending money
    self.state = 0                                          # Mark as done
    amt: uint256 = self.amount

    # Clear the money value so it can't be used again
    self.amount = 0                                         # No more money to give

    # Now we send money. Because state is changed first, a sneaky attacker can't call back quickly and steal more.
    send(self.seller, amt)                                  # Send the money to the seller
    log Released(seller=self.seller, amount=amt)            # Announce that money was released

# Buyer can get money back if too much time goes by (refund) 
@external
def refund():
    assert msg.sender == self.buyer, "permission denied"                                                    # Only the buyer can call refund
    assert self.state == 1, "contract has not been funded."                                                 # Only if contract is funded
    assert block.timestamp > self.start + self.timeout, "timeout has not passed"                            # Only after waiting enough time
    assert not self._all_conditions_fulfilled(), "all conditions have already been fulfilled"               # Only if not all conditions fulfilled

    # Again, CHANGE state first to 'refunded' so no tricks can happen!
    self.state = 0                                          # Mark as refunded
    amt: uint256 = self.amount
    self.amount = 0                                         # No more money to give

    # Now it's safe to send the money back
    send(self.buyer, amt)                                   # Send the money back to the buyer
    log Refunded(buyer=self.buyer, amount=amt)              # Announce that a refund happened
