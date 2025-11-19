import pytest

def test_deposit_and_release(contract, accounts):
    buyer, seller = accounts[0], accounts[1]
    contract.deposit({'from': buyer, 'value': 100})
    assert contract.amount() == 100
    contract.release({'from': seller})
    assert contract.state() == 2

def test_timeout_refund(contract, accounts, chain):
    buyer = accounts[0]
    contract.deposit({'from': buyer, 'value': 100})
    chain.sleep(contract.timeout() + 1)
    contract.refund({'from': buyer})
    assert contract.state() == 3
