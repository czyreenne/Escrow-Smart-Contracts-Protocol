from brownie import Escrow, accounts

def main():
    buyer = accounts[0]
    seller = accounts[1]
    timeout = 3600  # 1 hour
    contract = Escrow.deploy(seller, timeout, {'from': buyer})
    print(f"Deployed at: {contract.address}")
