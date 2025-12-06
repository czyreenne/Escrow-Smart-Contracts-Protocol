# Escrow Smart Contracts Protocol (MVP)

## Overview
A legally-aware, security-hardened escrow protocol implemented in Vyper for the Ethereum Sepolia testnet. Features simple deposit, release, auto-refund, strict access controls, reentrancy protection, and comprehensive event logging.

## Features
- Deposit–release workflow with buyer, seller, and timeout-based auto-refund
- Explicit state transitions, security against reentrancy
- Transparent events for auditability

## Quick Start
The instructions below are for running with local Ethereum Node Simulators (*ganache*)
1. Clone this repo
2. Set up virtual environment (`python -m venv venv`)
3. Navigate to virtual environment (`venv\Scripts\activate`)
4. Install dependencies in virtual environment (`pip install vyper` and set up web3 `pip install web3`)
5. Check that Vyper (`vyper --version`) and Web3 (`pip show web3`) are installed
6. In a separate terminal, ensure you have ganache installed (`npm install -g ganache`).
7. Then, start the local chain on ganache (`ganache`)
8. [Guide to deploy and test](docs/overview.md)
9. Compile Escrow.vy script and get abi (`vyper -f abi contracts/Escrow.vy > contracts/Escrow.abi`) and bytecode (`vyper -f bytecode contracts/Escrow.vy > contracts/Escrow.bin`)
10. Set deployer address as an environment variable
(For PS terminals -> `$Env:DEPLOYER_ADDRESS="0xYOUR_ADDRESS"`; For Linux/Mac -> `export DEPLOYER_ADDRESS="0xYOUR_ADDRESS"`)
11. Input deployer private key when prompted
12. Input seller address when deploying (`python scripts/deploy.py <seller_address> <timeout>`)

## Interacting with the Contract
1. Once the contract has been deployed, set the deployer private key (`$Env:BUYER_PRIVATE_KEY="0xBUYER_PRIVATE_KEY"`) and seller private key (`$Env:SELLER_PRIVATE_KEY="0xSELLER_PRIVATE_KEY"`) for signing transactions.
Note: *Seller address should belong to a different test account than the private key test account. In our case, the deployer is the same as the buyer.*
2. Verify set environment variables (`echo $Env:DEPLOYER_PRIVATE_KEY`, `echo $Env:BUYER_PRIVATE_KEY`, `echo $Env:SELLER_PRIVATE_KEY`)
3. Run interact.py - general usage: `python scripts/interact.py NAME_OF_SCENARIO <arguments>`.
4. To test with a fresh contract / clean state, REDEPLOY the contract with `python scripts/deploy.py <seller_address>`.

Note the following:
- Stateful and Immutable property of smart contracts. Once your contract finishes a workflow (like deposit and release), its state can’t be reset or reused, so running the same tests again won’t work unless you deploy a fresh contract instance.
- The functions are not unit tests. This means that attempting a release of funds (`python scripts/interact.py release`) before a deposit (`python scripts/interact.py deposit`) should throw an error/receipt status 0.
- Some functions like fulfill_conditions may require additional arguments. There should be a message with the required usage.(E.g. `python scripts/interact.py fulfill_conditions idx1 idx2`)

Example of interact.py output [Deposit - Fulfil ALL Conditions - Release]:
<pre><code>python scripts/interact.py deposit
Running deposit workflow

Deposit event test: Buyer deposits to escrow


 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059 | Balance: 988859355700000000000
Seller:  0x3bb560C961616430c4f1974243c6a3c0E99B129f | Balance: 1006991316640000000000
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

Checking for Deposited event...
[{'buyer': '0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059', 'amount': 1000000000000000000}]

=== Full Audit Trail ===

Scenario: deposit
TX Hash: 354b3052ece58f28ecea8ea24f85c8cecfc77deca7a95c0111f481f960fa0c54
State: 1
Buyer Balance: 988859355700000000000
Seller Balance: 1006991316640000000000
Contract Balance: 1000000000000000000
Amount Locked: 1000000000000000000
Events: [{'buyer': '0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059', 'amount': 1000000000000000000}]
Status: 1
------------------------------------------------
python scripts/interact.py release
Running release workflow

Release event test: Seller releases funds


 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059 | Balance: 988859355700000000000
Seller:  0x3bb560C961616430c4f1974243c6a3c0E99B129f | Balance: 1006990720180000000000
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

Checking for Released event...

=== Full Audit Trail ===

Scenario: release
TX Hash: e871c38801ccc10a00d5bfc555845665d4e88006fb33c855fce6191e0f410a7b
State: 1
Buyer Balance: 988859355700000000000
Seller Balance: 1006990720180000000000
Amount Locked: 1000000000000000000
Events: []
Status: 0
------------------------------------------------
python scripts/interact.py fulfill_all_conditions
Fulfilling ALL contract conditions.
  Condition 0 fulfilled.
  Condition 1 fulfilled.
  Condition 2 fulfilled.
All conditions fulfilled.


=== Full Audit Trail ===
PS C:\Users\Serene Sim\Documents\GitHub\Escrow-Smart-Contracts-Protocol> python scripts/interact.py release
Running release workflow

Release event test: Seller releases funds


 Current Contract State
State  (0=Init, 1=Funded): 0
Buyer:   0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059 | Balance: 988856413780000000000
Seller:  0x3bb560C961616430c4f1974243c6a3c0E99B129f | Balance: 1007989893760000000000
Contract balance: 0
Amount locked: 0

Checking for Released event...
[{'seller': '0x3bb560C961616430c4f1974243c6a3c0E99B129f', 'amount': 1000000000000000000}]

=== Full Audit Trail ===

Scenario: release
TX Hash: e90f72e7db91815b918936ea510bc84747c106b618f473cde126b57f5052b6e6
State: 0
Buyer Balance: 988856413780000000000
Seller Balance: 1007989893760000000000
Contract Balance: 0
Amount Locked: 0
Events: [{'seller': '0x3bb560C961616430c4f1974243c6a3c0E99B129f', 'amount': 1000000000000000000}]
Status: 1
------------------------------------------------</code></pre>

Another example of interact.py output [Deposit - Partial Fulfilment and Refund]:
<pre><code>python scripts/interact.py deposit                                 
Running deposit workflow

Deposit event test: Buyer deposits to escrow


 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059 | Balance: 985825054800000000000
Seller:  0x3bb560C961616430c4f1974243c6a3c0E99B129f | Balance: 1007989893760000000000
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

Checking for Deposited event...
[{'buyer': '0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059', 'amount': 1000000000000000000}]

=== Full Audit Trail ===

Scenario: deposit
TX Hash: e9a63dfedc5486213f7720bf2dc2931637731ecfc1e918b1e6b6f5d0fb933e66
State: 1
Buyer Balance: 985825054800000000000
Seller Balance: 1007989893760000000000
Contract Balance: 1000000000000000000
Amount Locked: 1000000000000000000
Events: [{'buyer': '0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059', 'amount': 1000000000000000000}]
Status: 1
------------------------------------------------
python scripts/interact.py partial_fulfillment_and_refund:2        

=== Partial Fulfillment Then Refund (Should NOT Succeed) ===
Fulfilling 2 contract conditions (simulate partial fulfillment).
  Condition 0 fulfilled.
  Condition 1 fulfilled.
Partial fulfill step complete.

 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x5AEF5E434CFDca42dcDE0491e1e0FA4ebE506059 | Balance: 985822542400000000000
Seller:  0x3bb560C961616430c4f1974243c6a3c0E99B129f | Balance: 1007989893760000000000
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

Refund failed as expected.

=== Full Audit Trail ===

Scenario: partial_fulfillment_and_refund
TX Hash: a22b26843ae7258ca7eefc0eabaa8b6ff0d5dedd27c3087e9a4e81acc290ad2d
State: 1
Buyer Balance: 985822542400000000000
Seller Balance: 1007989893760000000000
Contract Balance: 1000000000000000000
Amount Locked: 1000000000000000000
Events: []
Status: 0
Message: Refund failed as expected.
------------------------------------------------</code></pre>

## Test Scripts
[Guide to Automated Test Suite](tests/README.md)

## Closely Related Work
1. Centralized Escrow Services (e.g., PayPal, traditional banks)
Centralized escrows rely on manual processes, legal contracts, and trusted third-party intermediaries. While they are familiar and regulated, these services often suffer from slow operations due to paperwork, currency disagreements, and lengthy dispute resolution. Users face high service fees, limited customizability, and opaque transaction records. Furthermore, centralization introduces single-point-of-failure risks, including incompetence or dishonesty by escrow agents, and can lock up funds unnecessarily. As seen with cases involving PayPal, dissatisfied users regularly encounter service frustrations, restricted dispute outcomes, and inconsistent support, demonstrating the limitations of legacy escrow providers.

2. Smart Contract Escrow Platforms (e.g., OpenZeppelin Escrow)
Smart contract platforms automate escrow logic with on-chain code, reducing intermediary dependence and providing transparency. These solutions feature customizable conditions and timeouts, lower costs for large transactions, and event-based audit trails. However, they require technical expertise for deployment and interaction, limiting accessibility for non-technical users. Publicly available contract code exposes possible security vulnerabilities, making strong audits crucial. While programmable, smart contract escrows struggle with enforcing subjective or off-chain conditions, often necessitating human or off-chain intervention in disputes. Flexibility comes with a tradeoff: unless sufficiently audited and designed, funds may be at risk due to bugs or poor contract logic.

3. Decentralized Marketplaces (e.g., OpenSea)
Decentralized marketplace escrows embed basic trade logic within platform protocols, enabling peer-to-peer global asset exchanges without trusted intermediaries. These systems excel in speed, efficiency, and multi-asset/blockchain support, lowering transaction friction and costs. However, their escrow functionalities are typically limited to straightforward buy-sell logic, lacking multi-condition or milestone management. Dispute resolution is minimal or off-chain, and regulatory compliance can be uncertain, especially across jurisdictions. The absence of flexible, programmable condition enforcement makes them less suitable for complex arrangements or high-value regulated transactions. Vulnerabilities and platform exploits further highlight the need for robust security and legal recourse.

4. Other repositories(https://github.com/AleRapchan/escrow-service/tree/master):
This project is a Solidity-based smart contract implementing the escrow blockchain design pattern, and it can be deployed using Remix IDE or Truffle for local deployment. It works as a proof-of-concept demonstrating the sequential transaction flow required, along with Role-based Access Control (RBAC) patterns. 
- (a) Escrow agent deploys the smart contract with the buyer's address, seller's address, and transaction value.
- (b) The buyer sends payment to the contract, which locks the funds in a vault while automatically transferring 1ETH to the agent.
- (c) After the seller claims to have delivered the product, the buyer can either confirm receipt or deny elivery.
- (d) If the buyer denies delivery, the escrow agent has the authority to confirm the transaction (releasing funds) or cancelling it (returning funds to buyer) based on the investigation.

Instead of relying on centralized intermediaries (e.g. Escrow Agent) and manual confirmation (from the seller), our project aims to better highlight blockchain's strengths by reflecting more sophisticated condition logic, automatic detection of condition fulfilment, and automatic execution of release/refund operations. 

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
