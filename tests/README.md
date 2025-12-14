## Test Directory Structure
The testing suite consists of the following files:
- `test_deploy.py`: Python script with a function to deploy the contract without requiring manual input of the deployer's private key, allowing for multiple contract redeployments quickly to simulate a clean room environment. 
- `test_escrow.py`: Runs eight manually drafted test cases, deploying a fresh contract for each case
- `fuzz_test.py`: Testing with randomised inputs and sequence of operations, up to n iterations (can be changed within the script itself)

## Instructions
This test suite doesn't require you to input any addresses/private keys every single time, but the following environment variables are necessary to start:
- `export DEPLOYER_PRIVATE_KEY='0xYOUR_PK'`
- `export BUYER_PRIVATE_KEY='0xBUYER_PK'`
- `export SELLER_PRIVATE_KEY='0xSELLER_PK'`

Then, simply run `python3 tests/<SCRIPT.py>` and the test suite should run. 

Note: *Currently, fuzz_test.py follows this structure: call deposit with random amounts ->  add random conditions -> fulfil random conditions -> run release/refund randomly up to 3 times* (WIP: this should be made completely random)

## Sample Output for tests/test_escrow.py
First manual test in test_escrow.py output [Double Deposit -> second deposit should fail]:
<pre><code>python3 tests/test_escrow.py
---TESTS BEGIN NOW---

Deployment TX hash: 3f8e7f05b5dc28ff4dc9a657b396e2c366db528418a578c60fc8141d361e4687
Contract deployed at: 0xf6993CF35e56934A41c3f50efEC7AEA85Dd9cdcb
Testing repeated deposit...
===Attempting First Deposit===
Deposit Succeeded!
===Attempting Second Deposit===
Deposit Failed.</code></pre>

Another manual test in test_escrow.py output [Partial Completion of Conditions -> release of funds should fail]
<pre><code>Deployment TX hash: 2812b7f5ecd84b035284b9631defe3845bae4b57332a46516a863738bef9cd98
Contract deployed at: 0xA8AdCF95509794926354ff002522D578B93b9DfE
===Attempting to add condition 0===
Condition added: Random condition
===Attempting to add condition 1===
Condition added: Random condition
===Completing Condition===
    Condition 0 fulfilled.
Condition(s) fulfilled
===Attempting Early Release===
Release failed.
===Checking conditions===
Total Conditions: 2
Condition 0: Random condition | Fulfilled: True
Condition 1: Random condition | Fulfilled: False</code></pre>

## Sample Output for tests/fuzz_test.py
Example of test in fuzz_test.py output (deposit value in wei):
<pre><code>=== Fuzz iteration 149 ===
ConditionVerifier deployed at: 0xEdD6B6EAdE8a1f603431AcBbE02514d8AFaF6781
Condition created with ID: 0
Escrow deployed at: 0x6F064dA3df181D90d255BD48a485619B691F1422
🌀 Running 9 randomized ops (from 13 total ops)...
[1867] add_conditions → ✅...
✅ add_conditions succeeded
PRE-SIM FAIL add_conditions: generic revert (likely auth/state)
[1868] add_conditions → ❌PRE-SIM FAIL...
[1869] add_conditions → ✅...
✅ add_conditions succeeded
PRE-SIM ERROR release: {'message': 'VM Exception while processing transaction: invalid opcode', 'stack': 'CallError: VM 
Exception while processing transaction: invalid opcode\n    at Blockchain.simulateTransaction (C:\\Users\\Serene Sim\\AppData\\Roaming\\npm\\node_modules\\ganache\\dist\\node\\1.js:2:100650)', 'code': -32000, 'name': 'CallError', 'data': '0x'}
[1870] release → ❌PRE-SIM FAIL...
[1871] deposit → ✅...
✅ deposit succeeded
[1872] fulfill_condition → ✅...
✅ fulfill_condition succeeded
PRE-SIM FAIL fulfill_condition: generic revert (likely auth/state)
[1873] fulfill_condition → ❌PRE-SIM FAIL...
PRE-SIM ERROR deposit: {'message': 'VM Exception while processing transaction: invalid opcode', 'stack': 'CallError: VM 
Exception while processing transaction: invalid opcode\n    at Blockchain.simulateTransaction (C:\\Users\\Serene Sim\\AppData\\Roaming\\npm\\node_modules\\ganache\\dist\\node\\1.js:2:100650)', 'code': -32000, 'name': 'CallError', 'data': '0x'}
[1874] deposit → ❌PRE-SIM FAIL...
PRE-SIM ERROR release: {'message': 'VM Exception while processing transaction: invalid opcode', 'stack': 'CallError: VM 
Exception while processing transaction: invalid opcode\n    at Blockchain.simulateTransaction (C:\\Users\\Serene Sim\\AppData\\Roaming\\npm\\node_modules\\ganache\\dist\\node\\1.js:2:100650)', 'code': -32000, 'name': 'CallError', 'data': '0x'}
[1875] release → ❌PRE-SIM FAIL...
📊 Iteration success rate: 25.0%
=== Iteration complete ===</code></pre>
