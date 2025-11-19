import os
import sys
from web3 import Web3
import json

if len(sys.argv) < 2:
    print("Usage: python deploy.py <seller_address>")
    sys.exit(1)

seller_address = sys.argv[1]

private_key = os.environ.get('DEPLOYER_PRIVATE_KEY')
if not private_key:
    raise Exception("Environment variable DEPLOYER_PRIVATE_KEY is not set")

# Paste your compiled contract ABI JSON here
escrow_abi = json.loads('''[{"name": "Deposited", "inputs": [{"name": "buyer", "type": "address", "indexed": false}, {"name": "amount", "type": "uint256", "indexed": false}], "anonymous": false, "type": "event"}, {"name": "Released", "inputs": [{"name": "seller", "type": "address", "indexed": false}, {"name": "amount", "type": "uint256", "indexed": false}], "anonymous": false, "type": "event"}, {"name": "Refunded", "inputs": [{"name": "buyer", "type": "address", "indexed": false}, {"name": "amount", "type": "uint256", "indexed": false}], "anonymous": false, "type": "event"}, {"stateMutability": "payable", "type": "function", "name": "deposit", "inputs": [], "outputs": []}, {"stateMutability": "nonpayable", "type": "function", "name": "release", "inputs": [], "outputs": []}, {"stateMutability": "nonpayable", "type": "function", "name": "refund", "inputs": 
[], "outputs": []}, {"stateMutability": "view", "type": "function", "name": "buyer", "inputs": [], "outputs": [{"name": "", "type": "address"}]}, {"stateMutability": "view", "type": "function", "name": "seller", "inputs": [], "outputs": [{"name": "", "type": "address"}]}, {"stateMutability": "view", "type": "function", "name": "timeout", "inputs": [], "outputs": [{"name": "", "type": "uint256"}]}, {"stateMutability": "view", "type": "function", "name": "start", "inputs": [], "outputs": [{"name": "", "type": "uint256"}]}, {"stateMutability": "view", "type": "function", "name": "amount", "inputs": [], "outputs": [{"name": "", "type": "uint256"}]}, {"stateMutability": "view", "type": "function", "name": "state", "inputs": [], "outputs": [{"name": "", "type": "uint8"}]}, {"stateMutability": "nonpayable", "type": "constructor", "inputs": [{"name": "_seller", "type": "address"}, {"name": "_timeout", "type": "uint256"}], "outputs": []}]''')

# Paste your compiled contract bytecode here
escrow_bytecode = "0x346100475760206102ad5f395f518060a01c61004757604052335f5560405160015560206102cd5f395f51600255426003555f60055561022c61004b6100003961022c610000f35b5f80fd5f3560e01c60026007820660011b61021e01601e395f51565b63d0e30db081186100715760055461021a575f54331861021a57341561021a573460045560016005557f2da466a7b24304f47e87fa2e1e5a81b9831ce54fec19055ce277ca2f39ba42c4336040523460605260406040a1005b6308551a538118610216573461021a5760015460405260206040f35b6386d1a69f8118610216573461021a5760016005541861021a57600154331861021a5760026005556004546040525f6004555f5f5f5f6040516001545ff11561021a577fb21fb52d5749b80f3182f8c6992236b5e5576681880914484d7f4c9b062e619e60015460605260405160805260406060a1005b63590e1ae3811861018b573461021a5760016005541861021a5760035460025480820182811061021a579050905042111561021a5760036005556004546040525f6004555f5f5f5f6040515f545ff11561021a577fd7dee2702d63ad89917b6a4da9981c90c4d24f8c2bdfd64c604ecae57d8d06515f5460605260405160805260406060a1005b63be9a65558118610216573461021a5760035460405260206040f35b637150d8ae81186101c2573461021a575f5460405260206040f35b63c19d93fb8118610216573461021a5760055460405260206040f35b6370dea79a81186101fa573461021a5760025460405260206040f35b63aa8c217c8118610216573461021a5760045460405260206040f35b5f5ffd5b5f80fd0104001801a7008d0216021601de8558202be2a204f665106f0a26c1e077130a341b0fcf20abfb16e5635c12e6b15d156a19022c810e00a1657679706572830004030036"

# Connect to Ethereum node (adjust endpoint as needed)
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

if not w3.isConnected():
    raise Exception("Web3 provider is not connected")

deployer_address = w3.eth.account.privateKeyToAccount(private_key).address

timeout = 3600  # 1 hour timeout

Escrow = w3.eth.contract(abi=escrow_abi, bytecode=escrow_bytecode)

transaction = Escrow.constructor(seller_address, timeout).buildTransaction({
    'from': deployer_address,
    'nonce': w3.eth.getTransactionCount(deployer_address),
    'gas': 4000000,
    'gasPrice': w3.toWei('20', 'gwei')
})

signed_txn = w3.eth.account.signTransaction(transaction, private_key=private_key)

tx_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)

print(f"Transaction sent: {tx_hash.hex()}")

tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

print(f"Contract deployed at address: {tx_receipt.contractAddress}")
