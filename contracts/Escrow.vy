# SPDX-License-Identifier: MIT
# @version ^0.4.3

event Deposited:
    buyer: address
    amount: uint256

event Released:
    seller: address
    amount: uint256

event Refunded:
    buyer: address
    amount: uint256

buyer: public(address)
seller: public(address)
timeout: public(uint256)
start: public(uint256)
amount: public(uint256)
state: public(uint8)  # 0=INIT, 1=FUNDED, 2=RELEASED, 3=REFUNDED

@deploy
def __init__(_seller: address, _timeout: uint256):
    self.buyer = msg.sender
    self.seller = _seller
    self.timeout = _timeout
    self.start = block.timestamp
    self.state = 0

@payable
@external
def deposit():
    assert self.state == 0
    assert msg.sender == self.buyer
    assert msg.value > 0
    self.amount = msg.value
    self.state = 1
    log Deposited(buyer=msg.sender, amount=msg.value)

@external
def release():
    assert self.state == 1
    assert msg.sender == self.seller
    self.state = 2
    amt: uint256 = self.amount
    self.amount = 0
    send(self.seller, amt)
    log Released(seller=self.seller, amount=amt)

@external
def refund():
    assert self.state == 1
    assert block.timestamp > self.start + self.timeout
    self.state = 3
    amt: uint256 = self.amount
    self.amount = 0
    send(self.buyer, amt)
    log Refunded(buyer=self.buyer, amount=amt)
