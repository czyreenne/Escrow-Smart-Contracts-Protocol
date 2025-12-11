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

## Sample Interaction Flow 
**deposit -> add condition -> fulfill condition -> check condition fulfilment -> release of funds**

Example of interact.py output [Deposit]:
<pre><code>python3 scripts/interact.py deposit
Running deposit workflow

Deposit event test: Buyer deposits to escrow


 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x2b3351971771aB2E21eF3f67C5b5f52D26F999AE | Balance: 998980692240000000000
Seller:  0xce2FA53458A0D9dcF1221AbeD6223229090D899D | Balance: 1000000000000000000000
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

Checking for Deposited event...
[{'buyer': '0x2b3351971771aB2E21eF3f67C5b5f52D26F999AE', 'amount': 1000000000000000000}]

=== Full Audit Trail ===

Scenario: deposit
TX Hash: e8ac07a721868fef25a93aa87dd1e68d8cb11c54d4201d028aba0ca79e411310
State: 1
Buyer Balance: 998980692240000000000
Seller Balance: 1000000000000000000000
Contract Balance: 1000000000000000000
Amount Locked: 1000000000000000000
Events: [{'buyer': '0x2b3351971771aB2E21eF3f67C5b5f52D26F999AE', 'amount': 1000000000000000000}]
Status: 1
------------------------------------------------</code></pre>

Example of interact.py output [Add Condition]:
<pre><code>python3 scripts/interact.py add_conditions "Seller must call fulfill_condition"
Condition added: Seller must call fulfill_condition
Added condition event: [{'index': 0, 'description': 'Seller must call fulfill_condition'}]
Unknown test case: Seller must call fulfill_condition. *Note: just ignore this if you see an output when calling one of the non-main functions

=== Full Audit Trail ===</code></pre>

Example of interact.py output [Fulfill Condition at index 0]:
<pre><code>python3 scripts/interact.py fulfill_conditions 0
    Condition 0 fulfilled.

 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x2b3351971771aB2E21eF3f67C5b5f52D26F999AE | Balance: 998978267140000000000
Seller:  0xce2FA53458A0D9dcF1221AbeD6223229090D899D | Balance: 999988667800000000000
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

Condition(s) fulfilled
Unknown test case: 0. *Note: just ignore this if you see an output when calling one of the non-main functions

=== Full Audit Trail ===</code></pre>

Example of interact.py output [Check Conditions]:
<pre><code>python3 scripts/interact.py check_conditions
All conditions are fulfilled

=== Full Audit Trail ===</code></pre>

Example of interact.py output [Release]:
<pre><code>python3 scripts/interact.py release
Running release workflow

Release event test: Contract releases funds

 Current Contract State
State  (0=Init, 1=Funded): 0
Buyer:   0x2b3351971771aB2E21eF3f67C5b5f52D26F999AE | Balance: 998978267140000000000
Seller:  0xce2FA53458A0D9dcF1221AbeD6223229090D899D | Balance: 1000987930200000000000
Contract balance: 0
Amount locked: 0

Checking for Released event...
[{'seller': '0xce2FA53458A0D9dcF1221AbeD6223229090D899D', 'amount': 1000000000000000000}]

=== Full Audit Trail ===

Scenario: release
TX Hash: ea010217d29c05353cbe5f96c6f4523c9f779ed73be7c3a3cb02f63b2c3e7601
State: 0
Buyer Balance: 998978267140000000000
Seller Balance: 1000987930200000000000
Contract Balance: 0
Amount Locked: 0
Events: [{'seller': '0xce2FA53458A0D9dcF1221AbeD6223229090D899D', 'amount': 1000000000000000000}]
Status: 1
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

4. Other repositories (https://github.com/AleRapchan/escrow-service/tree/master):
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
