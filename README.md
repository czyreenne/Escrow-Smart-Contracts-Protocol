# Escrow Smart Contracts Protocol (MVP)

## Overview
A legally-aware, security-hardened escrow protocol implemented in Vyper for the Ethereum Sepolia testnet. Features simple deposit, release, auto-refund, strict access controls, reentrancy protection, and comprehensive event logging.

## Features
- Deposit–release workflow with buyer, seller, and timeout-based auto-refund
- Explicit state transitions, security against reentrancy
- Transparent events for auditability

## Quick Start
*python and python3 are used interchangeably below*

The instructions below are for running with local Ethereum Node Simulators (*ganache*)
1. Clone this repo
2. Set up virtual environment (`python -m venv venv`)
3. Navigate to virtual environment (`venv\Scripts\activate`)
4. Install dependencies in virtual environment (`pip install vyper` and set up web3 `pip install web3`)
5. Check that Vyper (`vyper --version`) and Web3 (`pip show web3`) are installed
6. In a separate terminal, ensure you have ganache installed (`npm install -g ganache`).
7. Then, start the local chain on ganache (`ganache`)
8. [Guide to deploy and test](docs/overview.md)
9. Compile Escrow.vy script and get abi (`vyper -f abi contracts/Escrow.vy > contracts/Escrow.abi`) and bytecode (`vyper -f bytecode contracts/Escrow.vy > contracts/Escrow.bin`).
10. Compile ConditionVerifier.vy script and get abi (`vyper -f abi contracts/ConditionVerifier.vy > contracts/ConditionVerifier.abi`) and bytecode (`vyper -f bytecode contracts/ConditionVerifier.vy > contracts/ConditionVerifier.bin`).
11. Set deployer address as an environment variable
(For PS terminals -> `$Env:DEPLOYER_ADDRESS="0xYOUR_ADDRESS"`; For Linux/Mac -> `export DEPLOYER_ADDRESS="0xYOUR_ADDRESS"`)
12. Input deployer private key when prompted
13. Input seller address when deploying (`python scripts/deploy.py <seller_address> <timeout> <beneficiary_address> <required_eth_amount_in_wei>`)

## Interacting with the Contract
1. Once the contract has been deployed, set the buyer private key (`$Env:BUYER_PRIVATE_KEY="0xBUYER_PRIVATE_KEY"`) and seller private key (`$Env:SELLER_PRIVATE_KEY="0xSELLER_PRIVATE_KEY"`) for signing transactions.
Note: *Seller address should belong to a different test account than the private key test account. In our case, the deployer is the same as the buyer.* Set deployer private key (`$Env:DEPLOYER_PRIVATE_KEY="0xDEPLOYER_PRIVATE_KEY"`) as well.
2. Verify set environment variables (`echo $Env:BUYER_PRIVATE_KEY`, `echo $Env:SELLER_PRIVATE_KEY`)
3. For automatic verification of condition fulfilment and release of Escrow funds, start a new terminal and start the keeper bot for it to listen for transactions. (`python scripts/keeperBot.py`). For manual testing, you can skip this step. 
4. Run interact.py - general usage: `python scripts/interact.py NAME_OF_SCENARIO <arguments>`. **Note that if the bot is listening, there is no need to manually call for release of Escrow funds with python scripts/interact.py release*
5. To test with a fresh contract / clean state, REDEPLOY the contract with `python scripts/deploy.py <seller_address>`.

**Note the following:**
- Stateful and Immutable property of smart contracts. Once your contract finishes a workflow (like deposit and release), its state can’t be reset or reused, so running the same tests again won’t work unless you deploy a fresh contract instance.
- The functions are not unit tests. This means that attempting a release of funds (`python scripts/interact.py release`) before a deposit (`python scripts/interact.py deposit`) should throw an error/receipt status 0.
- Some functions like fulfill_conditions may require additional arguments. There should be a message with the required usage.(E.g. `python scripts/interact.py fulfill_conditions idx1 idx2`)

## Example Deployment Output 
<pre><code>python3 scripts/deploy.py 0x65E66FB8b915A6F3edC37CDF4A4e4ef184c369F7 3600 0x98a99e8e0dd26BA6645935603F4Ad4A1C86eBeb9 1
Enter deployer private key: 
Deployer address: 0xc2595e5c48af7f2ab168376b2566ba5155b52ee1
Verified: deployment authorized for address 0xc2595e5c48af7f2ab168376b2566ba5155b52ee1

=== Step 1: Deploying ConditionVerifier ===
ConditionVerifier deployment TX hash: c6693460a768f55c898d1c9082f1157aca4f32e930c22cb739b7696ecbc78bca
ConditionVerifier deployed at: 0xF36E275C574ce0d8912c4846d5a0Bb7974F9c3A1

=== Step 2: Creating ETH deposit condition ===
Create condition TX hash: 07df66238b00f4f27dc0e5fb74feeb77d3916add12bf0ea3d9d9ced34af22902
Condition created with ID: 0

=== Step 3: Deploying Escrow ===
Escrow deployment TX hash: f53b8834f3fcf57416d0942e52896619dbd85a639461e4f0207c1cdce9e13a57
Escrow deployed at: 0x3351a5e950044A26849E1D51d279a57b3442B82F

ESCROW EVENTS (0x3351a5e950044A26849E1D51d279a57b3442B82F):
==================================================
INIT | State: 0

=== Step 4: Saving deployment records ===
Deployment recorded in testnet.json

=== Deployment Summary ===
ConditionVerifier: 0xF36E275C574ce0d8912c4846d5a0Bb7974F9c3A1
Condition ID: 0
Escrow: 0x3351a5e950044A26849E1D51d279a57b3442B82F
Seller: 0x65E66FB8b915A6F3edC37CDF4A4e4ef184c369F7
Beneficiary: 0x98a99e8e0dd26BA6645935603F4Ad4A1C86eBeb9
Required amount: 1 Wei (1E-18 ETH)
Timeout: 3600 seconds</pre></code>

## Sample Manual Interaction Flow 
See here for high-level flow: [docs/architecture diagram.png](https://github.com/czyreenne/Escrow-Smart-Contracts-Protocol/blob/main/docs/architecture%20diagram.png)
1. Start the bot -> bot listening
2. Deposit into Escrow.vy
3. Add condition
4. Fulfill condition
5. Check condition fulfilment
6. Deposit and Fulfil external condition (deposit_to_verifier)
7. ConditionVerifier emits event that the bot is listening for
8. Bot calls release of funds automatically
9. Print Escrow Summary and/or Full Audit Trail

- python3 scripts/interact.py deposit
- python3 scripts/interact.py add_conditions "deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF" (deposit funds to beneficiary)
- (for verification) python3 scripts/interact.py print_all_conditions
- python3 scripts/interact.py fulfill_conditions 0
- python3 scripts/interact.py check_conditions
- python3 scripts/interact.py deposit_to_verifier
- python3 scripts/interact.py full_audit

Example of starting the bot:
<pre><code>python3 scripts/keeperBot.py
============================================================
ESCROW KEEPER BOT INITIALIZATION
============================================================
Enter seller private key: 
Keeper bot initialized for seller: 0x65E66FB8b915A6F3edC37CDF4A4e4ef184c369F7

Loaded 1 escrow contract(s)
ConditionVerifier: 0xF36E275C574ce0d8912c4846d5a0Bb7974F9c3A1

============================================================
🤖 ESCROW KEEPER BOT STARTED
============================================================
Polling interval: 5 seconds
Press Ctrl+C to stop
============================================================

✓ Event filters set up
  Monitoring: ConditionFulfilled events from 0xF36E275C574ce0d8912c4846d5a0Bb7974F9c3A1</code></pre>

Example of interact.py output [Deposit]:
<pre><code>python3 scripts/interact.py deposit                                                                
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
💰 DEPOSIT WORKFLOW
✅ DEPOSIT SUCCEEDED!

🔍 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x340849B91117D16f1e0C12DC1DeD347EC963b7AA | Balance: 998958683000000000000  
Seller:  0x3b958F4E8489b3540c56d87121aB597D6ECef05d | Balance: 1000000000000000000000 
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

Deposited event: [{'buyer': '0x340849B91117D16f1e0C12DC1DeD347EC963b7AA', 'amount': 1000000000000000000}]</code></pre>

Example of interact.py output [Add Condition]:
<pre><code>python3 scripts/interact.py add_conditions "deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF"
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
📝 ADD CONDITIONS WORKFLOW
✅ Condition ADDED: 'deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF'
ConditionAdded event: [{'index': 0, 'description': 'deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF'}]
❓ Unknown: deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF

🚀 Commands:
  deposit | release | refund
  add_conditions "Text" | fulfill_conditions 0 1
  deposit_to_verifier | verify_external_condition
  print_all_conditions | escrow_summary | full_audit
</code></pre>

Example of interact.py output [Print All Conditions]:
<pre><code>python3 scripts/interact.py print_all_conditions
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
📋 Total Conditions: 1
  ❌ [0] deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF
</code></pre>

Example of interact.py output [Fulfill Condition at index 0]:
<pre><code>python3 scripts/interact.py fulfill_conditions 0
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
✅ FULFILL CONDITIONS WORKFLOW
✅ Condition 0 FULFILLED ✓

🔍 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x340849B91117D16f1e0C12DC1DeD347EC963b7AA | Balance: 998958561445000000000  
Seller:  0x3b958F4E8489b3540c56d87121aB597D6ECef05d | Balance: 999999943339000000000  
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

📋 Total Conditions: 1
  ✅ [0] deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF
❓ Unknown: 0

🚀 Commands:
  deposit | release | refund
  add_conditions "Text" | fulfill_conditions 0 1
  deposit_to_verifier | verify_external_condition
  print_all_conditions | escrow_summary | full_audit
</code></pre>

Example of interact.py output [Check Conditions]:
<pre><code>python3 scripts/interact.py check_conditions
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
All conditions are fulfilled
</code></pre>

Example of interact.py output [Deposit to Verifier]:
<pre><code>python3 scripts/interact.py deposit_to_verifier
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
🌐 EXTERNAL CONDITION WORKFLOW
Condition ID: 0
Required: Ξ 3.654279658035655
✅ Deposit to verifier SUCCEEDED!
TX: 3a6845847a4329af05dd72f89dff35397b91ba7d786aac16859870c13bcf731c
✅ External condition FULFILLED!
</code></pre>

Example of automated release (same terminal the bot was listening on):
<pre><code>✓ Event filters set up
  Monitoring: ConditionFulfilled events from 0xF36E275C574ce0d8912c4846d5a0Bb7974F9c3A1

🔔 NEW EVENT: ConditionFulfilled
   Condition ID: 0
   Timestamp: 2025-12-12 05:52:57

🤖 ATTEMPTING AUTO-RELEASE
   Escrow: 0x3351a5e950044A26849E1D51d279a57b3442B82F
   Seller: 0x65E66FB8b915A6F3edC37CDF4A4e4ef184c369F7
   ✓ Pre-check passed
   📤 Release TX sent: 557118c779c1f96739a3c0e585fb1b13094844840a59ef43dc3016a586de1d8c
/home/ryclin/projects/Escrow-Smart-Contracts-Protocol-v2/.venv/lib/python3.12/site-packages/eth_utils/functional.py:47: UserWarning: The log with transaction hash: HexBytes('0x557118c779c1f96739a3c0e585fb1b13094844840a59ef43dc3016a586de1d8c') and logIndex: 0 encountered the following error during processing: MismatchedABI(The event signature did not match the provided ABI). It has been discarded.
  return callback(fn(*args, **kwargs))
/home/ryclin/projects/Escrow-Smart-Contracts-Protocol-v2/.venv/lib/python3.12/site-packages/eth_utils/functional.py:47: UserWarning: The log with transaction hash: HexBytes('0x557118c779c1f96739a3c0e585fb1b13094844840a59ef43dc3016a586de1d8c') and logIndex: 2 encountered the following error during processing: MismatchedABI(The event signature did not match the provided ABI). It has been discarded.
  return callback(fn(*args, **kwargs))
   ✅ RELEASE SUCCESSFUL!
      Amount: 1 ETH
      Gas used: 74692</code></pre>

Example of interact.py output [Full Audit Trail]:
<pre><code>python3 scripts/interact.py full_audit
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0

🔍 EVENT DECODER (0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0):
================================================================================      
ABI Event: Deposited            → 2da466a7b24304f47e87fa2e1e5a81b9831ce54fec19055ce277ca2f39ba42c4
ABI Event: Released             → b21fb52d5749b80f3182f8c6992236b5e5576681880914484d7f4c9b062e619e
ABI Event: Refunded             → d7dee2702d63ad89917b6a4da9981c90c4d24f8c2bdfd64c604ecae57d8d0651
ABI Event: ConditionFulfilled   → c7104caeb6f835c836dbbc04d0ccee00c51e89a718def631c9d0e20878ccdc80
ABI Event: ConditionAdded       → a1cf80a32c29ea13fb276c75b3196c5610dad18c0bb8053eac8336b200889bf4
ABI Event: ExternalConditionChecked → f1ea5a2eaecc05cf34f347a10bc0efac75cbf98bb6f9685c82b8a74b22933293
ABI Event: EscrowStatus         → 8abb8eb32bea36df9bd1cf5605f44e11854ea29cef2ec948a458421eae631af7

Found 8 logs:
[ 0] ✅ EscrowStatus         | Block 3
     Sig: 8abb8eb32bea36df9bd1...
     Topic1: 00000000000000000000...
     Topic2: 00000000000000000000...
[ 1] ✅ Deposited            | Block 4
     Sig: 2da466a7b24304f47e87...
[ 2] ✅ EscrowStatus         | Block 4
     Sig: 8abb8eb32bea36df9bd1...
     Topic1: 00000000000000000000...
     Topic2: 00000000000000000000...
[ 3] ✅ ConditionAdded       | Block 5
     Sig: a1cf80a32c29ea13fb27...
[ 4] ✅ ConditionFulfilled   | Block 6
     Sig: c7104caeb6f835c836db...
[ 5] ✅ ExternalConditionChecked | Block 8
     Sig: f1ea5a2eaecc05cf34f3...
     Topic1: 00000000000000000000...
     Topic2: 00000000000000000000...
[ 6] ✅ Released             | Block 8
     Sig: b21fb52d5749b80f3182...
[ 7] ✅ EscrowStatus         | Block 8
     Sig: 8abb8eb32bea36df9bd1...
     Topic1: 00000000000000000000...
     Topic2: 00000000000000000000...
================================================================================  </code></pre>

Example of interact.py output [Refund]:
<pre><code>python3 scripts/interact.py refund
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
💸 REFUND WORKFLOW
⏩ Time advanced past timeout
✅ REFUND SUCCEEDED!

🔍 Current Contract State
State  (0=Init, 1=Funded): 0
Buyer:   0x340849B91117D16f1e0C12DC1DeD347EC963b7AA | Balance: 997958243169000000000  
Seller:  0x3b958F4E8489b3540c56d87121aB597D6ECef05d | Balance: 998342477368964345000  
Contract balance: 0
Amount locked: 0
</code></pre>

Example of interact.py output [Error handling]:
<pre><code>python3 scripts/interact.py deposit
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
💰 DEPOSIT WORKFLOW
❌ PRE-SIM FAIL deposit: 🛑 ALREADY FUNDED (State=1)

🔍 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x340849B91117D16f1e0C12DC1DeD347EC963b7AA | Balance: 997958488185000000000  
Seller:  0x3b958F4E8489b3540c56d87121aB597D6ECef05d | Balance: 997344052060964345000  
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000
</code></pre>
<pre><code>python3 scripts/interact.py fulfill_conditions 3
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
✅ FULFILL CONDITIONS WORKFLOW
❌ PRE-SIM FAIL fulfill_condition(3): 🛑 INDEX OUT OF BOUNDS (3 >= 2)

🔍 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x340849B91117D16f1e0C12DC1DeD347EC963b7AA | Balance: 996958290570000000000  
Seller:  0x3b958F4E8489b3540c56d87121aB597D6ECef05d | Balance: 998343477368964345000  
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

📋 Total Conditions: 2
  ✅ [0] deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF
  ❌ [1] deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF
❓ Unknown: 3

🚀 Commands:
  deposit | release | refund
  add_conditions "Text" | fulfill_conditions 0 1
  deposit_to_verifier | verify_external_condition
  print_all_conditions | escrow_summary | full_audit
</code></pre>
<pre><code>python3 scripts/interact.py release
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
🔓 RELEASE WORKFLOW
❌ PRE-SIM FAIL release: 🛑 NOT FUNDED (State≠1)

🔍 Current Contract State
State  (0=Init, 1=Funded): 0
Buyer:   0x340849B91117D16f1e0C12DC1DeD347EC963b7AA | Balance: 997958243169000000000  
Seller:  0x3b958F4E8489b3540c56d87121aB597D6ECef05d | Balance: 998342477368964345000  
Contract balance: 0
Amount locked: 0
</code></pre>
<pre><code>python3 scripts/interact.py release
0xb6df1bc11927d210ef49f4ac1e306b342f0ac4a86a9fdfdf54bfee2a8110ed9e
Connected to Escrow: 0xBa56eb22ed001B931fdbf08b5327F45a1fE1A9c0
Connected to ConditionVerifier: 0x4934A8c41d7e151F95C2D7852e11FC6B1A6E7Ee7
External Condition ID: 0
🔓 RELEASE WORKFLOW
❌ RELEASE FAILED: TX REVERTED (status=0)

🔍 Current Contract State
State  (0=Init, 1=Funded): 1
Buyer:   0x340849B91117D16f1e0C12DC1DeD347EC963b7AA | Balance: 996958045554000000000  
Seller:  0x3b958F4E8489b3540c56d87121aB597D6ECef05d | Balance: 998341977368964345000  
Contract balance: 1000000000000000000
Amount locked: 1000000000000000000

📋 Total Conditions: 3
  ✅ [0] deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF
  ❌ [1] deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF
  ❌ [2] deposit funds to 0xd22a3D2106DAa62B337D9b4650c711EB9E6de7EF
  </code></pre>

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
