# Escrow Smart Contracts Protocol (MVP)

## Overview
A legally-aware, security-hardened escrow protocol implemented in Vyper for the Ethereum Sepolia testnet. Features simple deposit, release, auto-refund, strict access controls, reentrancy protection, and comprehensive event logging.

## Features
- Deposit–release workflow with buyer, seller, and timeout-based auto-refund
- Explicit state transitions, security against reentrancy
- Transparent events for auditability

## Quick Start
1. Clone this repo
2. Set up virtual environment (`python -m venv venv`)
3. Navigate to virtual environment (`venv\Scripts\activate`)
4. Install dependencies in virtual environment (`pip install vyper` and set up web3 `pip install web3`)
5. Check that Vyper (`vyper --version`) and Web3 (`pip show web3`) are installed 
6. [Guide to deploy and test](docs/overview.md)
7. Compile Escrow.vy script and get abi (`vyper -f abi contracts/Escrow.vy > contracts/Escrow.abi`) and bytecode (`vyper -f bytecode contracts/Escrow.vy > contracts/Escrow.bin`)
8. Set deployer private key as an environment variable (For PS terminals -> `$Env:DEPLOYER_PRIVATE_KEY="0xYOUR_PRIVATE_KEY"`)
9. Input seller address when deploying (`python scripts/deploy.py 0xSELLER_ADDRESS`)

## Testing 
We identified 2 methods for testing:
- Using Local Ethereum Node Simulators 
- Using MetaMask for Testnets

Using Local Ethereum Node Simulators:
1. Install Ganache by Truffle Suite (`npm install -g ganache`)
2. Start Ganache on a terminal (`ganache`). CLI should display a list of Available Accounts and their corresponding Private Keys.
3. On another terminal, set deployer private key as one of the private keys available (`$Env:DEPLOYER_PRIVATE_KEY="0xYOUR_PRIVATE_KEY"`)
4. Run deploy.py (`python scripts/deploy.py 0xSELLER_ADDRESS`). Note: Seller address should belong to a different test account than the private key test account.
5. Set buyer private key (`$Env:BUYER_PRIVATE_KEY="0xBUYER_PRIVATE_KEY"`) and seller private key (`$Env:SELLER_PRIVATE_KEY="0xSELLER_PRIVATE_KEY"`) as OS variables. Use another 2 different private keys from the list of private keys provided by Ganache. Note: *In our case, the deployer is the same as the buyer.* Therefore, buyer private keys should belong to the same account used for deployment. Seller private key should be the private key belonging to the same account used for seller address.
6. Verify set environment variables (`echo $Env:DEPLOYER_PRIVATE_KEY`, `echo $Env:BUYER_PRIVATE_KEY`, `echo $Env:SELLER_PRIVATE_KEY`)
7. Run interact.py 
Usage: `python scripts/interact.py NAME_OF_SCENARIO(S)`
8. REDEPLOY the contract to retest after successful run. *Repeat steps 4 and 7.*
Note: Stateful and Immutable property of smart contracts. Once your contract finishes a workflow (like deposit and release), its state can’t be reset or reused, so running the same tests again won’t work unless you deploy a fresh contract instance.

Examples of commands used/OS variables set:
- `python scripts/deploy.py 0x3bb560C961616430c4f1974243c6a3c0E99B129f`
- `$Env:DEPLOYER_PRIVATE_KEY="0x4b7ebe9e5c43116f7a8366d8f30302de1ab46fe488daa8aafa6b5c96f8adc523" (Account 0)`
- `$Env:BUYER_PRIVATE_KEY="0x4b7ebe9e5c43116f7a8366d8f30302de1ab46fe488daa8aafa6b5c96f8adc523" (Account 0)`
- `$Env:SELLER_PRIVATE_KEY="0xba2128a3d4eca8c709b933e2fd3460f45f9ee73b213267d33fe54c24d1767727" (Account 1)`

Example of interact.py output:
<pre><code>Running deposit workflow

Deposit event test: Buyer deposits to escrow


 Current Contract State
State  (0=Init, 1=Funded, 2=Released, 3=Refunded): 1
Buyer:   0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059 | Balance: 991909201180000000000
Seller:  0x3bb560C961616430c4f1974243c6a3c0E99B129f | Balance: 1005993712720000000000
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

Checking for Deposited event...
[{'buyer': '0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059', 'amount': 1000000000000000000}]
Running release workflow

Release event test: Seller releases funds


 Current Contract State
State  (0=Init, 1=Funded, 2=Released, 3=Refunded): 2
Buyer:   0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059 | Balance: 991909201180000000000
Seller:  0x3bb560C961616430c4f1974243c6a3c0E99B129f | Balance: 1006992975400000000000
Contract balance: 0
Amount locked: 0

Checking for Released event...
[{'seller': '0x3bb560C961616430c4f1974243c6a3c0E99B129f', 'amount': 1000000000000000000}]

=== Refund After Release (Should Fail) ===

 Current Contract State
State  (0=Init, 1=Funded, 2=Released, 3=Refunded): 2
Buyer:   0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059 | Balance: 991908735760000000000
Seller:  0x3bb560C961616430c4f1974243c6a3c0E99B129f | Balance: 1006992509560000000000
Contract balance: 0
Amount locked: 0


 Current Contract State
State  (0=Init, 1=Funded, 2=Released, 3=Refunded): 2
Buyer:   0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059 | Balance: 991908269920000000000
Seller:  0x3bb560C961616430c4f1974243c6a3c0E99B129f | Balance: 1006992509560000000000
Contract balance: 0
Amount locked: 0

Refund failed as expected after release.

=== Full Audit Trail ===

Step: deposit
TX Hash: 4111a9e5d281f21b3d5b42e769f0e1a3b262e5651d8d034a86ba286e844e6a6a
State: 1
Buyer Balance: 991909201180000000000
Seller Balance: 1005993712720000000000
Contract Balance: 1000000000000000000
Amount Locked: 1000000000000000000
Events: [{'buyer': '0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059', 'amount': 1000000000000000000}]
Status: 1
------------------------------------------------

Step: release
TX Hash: 14a410df62370b09fa8f0273caeb6e8fe48c35e34a2586c22e05306ec650e350
State: 2
Buyer Balance: 991909201180000000000
Seller Balance: 1006992975400000000000
Contract Balance: 0
Amount Locked: 0
Events: [{'seller': '0x3bb560C961616430c4f1974243c6a3c0E99B129f', 'amount': 1000000000000000000}]
Status: 1
------------------------------------------------

Step: refund_after_release
TX Hash: 733ea030304161755507163a2b76539cf81201b4a58de33b2eda88d53eefdc5b
State: 2
Buyer Balance: 991908269920000000000
Seller Balance: 1006992509560000000000
Contract Balance: 0
Amount Locked: 0
Events: []
Status: 0
Message: Refund failed as expected after release.
------------------------------------------------</code></pre>

## Repo Structure
- `contracts/`: Vyper code (and interfaces)
- `tests/`: Test scripts (unit and edge-case)
- `scripts/`: Deploy and interact scripts
- `audits/`: Security reports
- `docs/`: Documentation and usage
Note: Interface and Security Reports might or might not be included, depending on whether time permits

## Authors
- Serene Sim Ann Chee (sacsim@kth.se)
- Randall Lin Yi Cong (ryclin@kth.se)

## License
MIT 
