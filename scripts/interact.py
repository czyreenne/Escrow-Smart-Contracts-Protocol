# Below are various interactions with the deployed contract for the purposes of the demo

# Reading contract state after deployment
from web3 import Web3
import json

with open('contracts/Escrow.abi') as f:
    abi = json.load(f)
contract = w3.eth.contract(address='<deployed-address>', abi=abi)
print("Contract buyer:", contract.functions.buyer().call())
