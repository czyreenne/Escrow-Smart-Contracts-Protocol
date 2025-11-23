# SPDX-License-Identifier: MIT
# @version ^0.4.3

# Events act as messages or signals. They help us know what happened inside the contract.
event Deposited:
    buyer: address    # Who sent the money
    amount: uint256   # How much money was sent

event Released:
    seller: address   # Who received money
    amount: uint256   # How much money was sent

event Refunded:
    buyer: address    # Who got money back
    amount: uint256   # How much money was refunded

# NEW: track condition status
event ConditionFulfilled:
    index: uint256            # Which condition
    status: bool              # True if fulfilled

# Main Players and Rules 
buyer: public(address)       # This person pays the seller (gets set when contract starts)
seller: public(address)      # This person receives money from the buyer
timeout: public(uint256)     # How long before the buyer can get a refund
start: public(uint256)       # When the contract started
amount: public(uint256)      # How much money is in the contract
state: public(uint8)         # What is happening? 0 = not funded, 1 = funded

# NEW: Support for dynamic conditions
conditions: public(HashMap[uint256, bool])  # Which conditions have been fulfilled
num_conditions: public(uint256)             # Total conditions required
max_conditions: constant(uint256) = 32  # a safe upper bound, required for specifying a literal in range, and not a dynamic int variable

# What happens when the contract is created 
@deploy
def __init__(_seller: address, _timeout: uint256, _num_conditions: uint256):
    self.buyer = msg.sender         # The person starting the contract is the buyer
    self.seller = _seller           # The seller's address
    self.timeout = _timeout         # How long before refund is possible
    self.start = block.timestamp    # Remember when we started
    self.state = 0                  # Start in 'not funded' state
    self.num_conditions = _num_conditions  # Set the number of required conditions
    # Set all initial condition statuses to False (not fulfilled)
    for i: uint256 in range(max_conditions):
        if i >= _num_conditions:
            break
        self.conditions[i] = False

# Buyer puts money in (deposit) 
@payable
@external
def deposit():
    assert self.state == 0                    # Only if not funded already
    assert msg.sender == self.buyer           # Only the buyer may deposit
    assert msg.value > 0                      # Must send some money
    self.amount = msg.value                   # Save how much was sent
    self.state = 1                            # Now we are funded
    log Deposited(buyer=msg.sender, amount=msg.value)  # Announce that a deposit happened

# NEW: Mark a condition fulfilled
@external
def fulfill_condition(index: uint256):
    # In production, add permission control for marking conditions!
    assert self.state == 1
    assert index < self.num_conditions
    self.conditions[index] = True
    log ConditionFulfilled(index=index, status=True)

# NEW: Check if all conditions are fulfilled
@view
def all_conditions_fulfilled() -> bool:
    for i: uint256 in range(max_conditions):
        if i >= self.num_conditions:
            break
        if not self.conditions[i]:
            return False
    return True

# Seller can claim money (release) 
@external
def release():
    assert self.state == 1                     # Only if contract is funded 
    assert msg.sender == self.seller           # Only the seller can claim
    assert self.all_conditions_fulfilled()     # Only if all conditions fulfilled
    # Prevention of REENTRANCY attacks: Change contract state to 'done' BEFORE sending money
    self.state = 0                             # Mark as done
    amt: uint256 = self.amount
    # Clear the money value so it can't be used again
    self.amount = 0                            # No more money to give
    # Now we send money. Because state is changed first, a sneaky attacker can't call back quickly and steal more.
    send(self.seller, amt)                     # Send the money to the seller
    log Released(seller=self.seller, amount=amt)       # Announce that money was released

# Buyer can get money back if too much time goes by (refund) 
@external
def refund():
    assert self.state == 1                                   # Only if contract is funded
    assert block.timestamp > self.start + self.timeout       # Only after waiting enough time
    assert not self.all_conditions_fulfilled()               # Only if not all conditions fulfilled
    # Again, CHANGE state first to 'refunded' so no tricks can happen!
    self.state = 0                                           # Mark as refunded
    amt: uint256 = self.amount
    self.amount = 0                                          # No more money to give
    # Now it's safe to send the money back
    send(self.buyer, amt)                                    # Send the money back to the buyer
    log Refunded(buyer=self.buyer, amount=amt)               # Announce that a refund happened
