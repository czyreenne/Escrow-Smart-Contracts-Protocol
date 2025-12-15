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

### All test cases for test_escrow
1. REPEATED DEPOSIT          → FAIL (already funded)
2. EARLY RELEASE             → FAIL (internal condition unfulfilled)  
3. EDGE TIMEOUT              → FAIL/SUCCESS boundary testing
4. REFUND AFTER COMPLETION   → FAIL (conditions fulfilled → no refund)
5. INVALID INDEX + MAX CONDS → FAIL (11th condition) + SUCCESS (full flow)
6. PARTIAL COMPLETION        → FAIL (1/2 conditions fulfilled)
7. ZERO CONDITIONS           → SUCCESS (external only)
8. EMPTY DESCRIPTION         → SUCCESS (no restrictions)

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

## All tests for fuzz_test.py
1. Internal Conditions (Escrow)
`deposit()` → Already funded (State=1), random amounts
`add_conditions()` → Empty strings, unicode ☃★♠™, 90-100 char overflow
`fulfill_condition()` → OOB indices (-5 to +5 overflow), double-fulfill

2. External Conditions (ConditionVerifier)
`deposit_eth()` → Under required (0.1-0.9 ETH), over required (1.1-3 ETH), already fulfilled

3. State Transitions
`release()` → Not funded (State≠1), internal unfilled, external unfilled
`refund()` → Not funded, timeout boundary (7200s fast-forward)

4. Chaos Patterns
8-15 randomly selected operations for each fuzz run.

5. Large number of fuzz runs
150 fuzz runs.

## Sample Output for tests/fuzz_test.py
Example of test in fuzz_test.py output (deposit value in wei):
<pre><code>=== Fuzz iteration 146 ===
ConditionVerifier deployed at: 0x7e7944EAec6076F5C6c92E54F8EEd3Cf13d60a88
Condition created with ID: 0
Escrow deployed at: 0xE4fb507778ec0d2cDA133bFC50f85306036E6B02
[2444] DEPLOY → ✅ 
🆕 Deployed: 0xE4fb507778ec0d2cDA133bFC50f85306036E6B02 (CV: 0x7e7944EAec6076F5C6c92E54F8EEd3Cf13d60a88, Cond: 0)
🌀 Running 14 randomized ops (from 12 total ops)...
[2445] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2446] fulfill_condition_PRECHECK_FAIL → ❌ 📏 🛑 INDEX OUT OF BOUNDS (9 >= 0)...
PRE-SIM FAIL fulfill_condition: 🛑 INDEX OUT OF BOUNDS (9 >= 0)
[2447] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2448] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2449] deposit → ✅ 
✅ deposit succeeded
[2450] add_conditions → ✅ 
✅ add_conditions succeeded
[2451] fulfill_condition → ✅ 
✅ fulfill_condition succeeded
[2452] add_conditions → ✅ 
✅ add_conditions succeeded
[2453] add_conditions → ❌ 🛑 TX REVERTED...
❌ add_conditions TX REVERTED: 🛑 TX REVERTED
[2454] release → ❌ 🔄 🛑 NOT ALL CONDITIONS FULFILLED...
❌ release TX REVERTED: 🛑 NOT ALL CONDITIONS FULFILLED
[2455] add_conditions → ✅ 
✅ add_conditions succeeded
[2456] refund → ✅ 
✅ refund succeeded
[2457] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2458] fulfill_condition_PRECHECK_FAIL → ❌ 📏 🛑 INDEX OUT OF BOUNDS (9 >= 3)...
PRE-SIM FAIL fulfill_condition: 🛑 INDEX OUT OF BOUNDS (9 >= 3)
📊 Iteration success rate: 36.0%
=== Iteration complete ===

=== Fuzz iteration 147 ===
ConditionVerifier deployed at: 0xECfE3fFEc3c086F9A60Fb0D75d48b52759259a96
Condition created with ID: 0
Escrow deployed at: 0x8AeA0fbD385b3232E85bfc4E37221a11bfE689F2
[2460] DEPLOY → ✅ 
🆕 Deployed: 0x8AeA0fbD385b3232E85bfc4E37221a11bfE689F2 (CV: 0xECfE3fFEc3c086F9A60Fb0D75d48b52759259a96, Cond: 0)
🌀 Running 16 randomized ops (from 25 total ops)...
[2461] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2462] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2463] fulfill_condition_PRECHECK_FAIL → ❌ 📏 🛑 INDEX OUT OF BOUNDS (2 >= 0)...
PRE-SIM FAIL fulfill_condition: 🛑 INDEX OUT OF BOUNDS (2 >= 0)
[2464] deposit → ✅ 
✅ deposit succeeded
[2465] deposit_eth → ✅ 🌐 
✅ deposit_eth succeeded
[2466] fulfill_condition_PRECHECK_FAIL → ❌ 📏 🛑 INDEX OUT OF BOUNDS (8 >= 0)...
PRE-SIM FAIL fulfill_condition: 🛑 INDEX OUT OF BOUNDS (8 >= 0)
[2467] refund → ❌ 🛑 TX REVERTED...
❌ refund TX REVERTED: 🛑 TX REVERTED
[2468] fulfill_condition_PRECHECK_FAIL → ❌ 📏 🛑 INDEX OUT OF BOUNDS (11 >= 0)...
PRE-SIM FAIL fulfill_condition: 🛑 INDEX OUT OF BOUNDS (11 >= 0)
[2469] add_conditions → ✅ 
✅ add_conditions succeeded
[2470] add_conditions → ❌ 🛑 TX REVERTED...
❌ add_conditions TX REVERTED: 🛑 TX REVERTED
[2471] deposit_PRECHECK_FAIL → ❌ 💰 🛑 ALREADY FUNDED (State=1)...
PRE-SIM FAIL deposit: 🛑 ALREADY FUNDED (State=1)
[2472] deposit_PRECHECK_FAIL → ❌ 💰 🛑 ALREADY FUNDED (State=1)...
PRE-SIM FAIL deposit: 🛑 ALREADY FUNDED (State=1)
[2473] refund → ✅ 
✅ refund succeeded
[2474] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2475] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2476] deposit_eth → ❌ 🌐 🛑 UNKNOWN CV REVERT...
❌ deposit_eth TX REVERTED: 🛑 UNKNOWN CV REVERT
📊 Iteration success rate: 32.0%
=== Iteration complete ===

=== Fuzz iteration 148 ===
ConditionVerifier deployed at: 0x05426c793Ea181b8a4C8Ef98590Ba8A389b04cA7
Condition created with ID: 0
Escrow deployed at: 0x91F9dcb5a53A44CdC3b0d84b7cc68260f421E9b7
[2478] DEPLOY → ✅ 
🆕 Deployed: 0x91F9dcb5a53A44CdC3b0d84b7cc68260f421E9b7 (CV: 0x05426c793Ea181b8a4C8Ef98590Ba8A389b04cA7, Cond: 0)
🌀 Running 13 randomized ops (from 17 total ops)...
[2479] release_PRECHECK_FAIL → ❌ 💰 🛑 NOT FUNDED (State≠1)...
PRE-SIM FAIL release: 🛑 NOT FUNDED (State≠1)
[2480] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2481] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2482] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2483] release_PRECHECK_FAIL → ❌ 💰 🛑 NOT FUNDED (State≠1)...
PRE-SIM FAIL release: 🛑 NOT FUNDED (State≠1)
[2484] deposit_eth → ✅ 🌐 
✅ deposit_eth succeeded
[2485] refund_PRECHECK_FAIL → ❌ 💰 🛑 NOT FUNDED (State≠1)...
PRE-SIM FAIL refund: 🛑 NOT FUNDED (State≠1)
[2486] deposit_eth → ✅ 🌐 
✅ deposit_eth succeeded
[2487] deposit_eth → ❌ 🌐 🛑 UNKNOWN CV REVERT...
❌ deposit_eth TX REVERTED: 🛑 UNKNOWN CV REVERT
[2488] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2489] deposit_eth → ❌ 🌐 🛑 UNKNOWN CV REVERT...
❌ deposit_eth TX REVERTED: 🛑 UNKNOWN CV REVERT
[2490] release_PRECHECK_FAIL → ❌ 💰 🛑 NOT FUNDED (State≠1)...
PRE-SIM FAIL release: 🛑 NOT FUNDED (State≠1)
[2491] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
📊 Iteration success rate: 20.0%
=== Iteration complete ===

=== Fuzz iteration 149 ===
ConditionVerifier deployed at: 0xC598907E092459e7a777f61127d4151D6fb9159D
Condition created with ID: 0
Escrow deployed at: 0x6b5766e6587Fe53B8A34B6a8E8F2254fe747C63F
[2493] DEPLOY → ✅ 
🆕 Deployed: 0x6b5766e6587Fe53B8A34B6a8E8F2254fe747C63F (CV: 0xC598907E092459e7a777f61127d4151D6fb9159D, Cond: 0)
🌀 Running 11 randomized ops (from 13 total ops)...
[2494] deposit_eth → ✅ 🌐 
✅ deposit_eth succeeded
[2495] fulfill_condition_PRECHECK_FAIL → ❌ 📏 🛑 INDEX OUT OF BOUNDS (1 >= 0)...
PRE-SIM FAIL fulfill_condition: 🛑 INDEX OUT OF BOUNDS (1 >= 0)
[2496] add_conditions_PRECHECK_FAIL → ❌ 💰 🛑 MUST BE FUNDED FIRST (State=1)...
PRE-SIM FAIL add_conditions: 🛑 MUST BE FUNDED FIRST (State=1)
[2497] fulfill_condition_PRECHECK_FAIL → ❌ 📏 🛑 INDEX OUT OF BOUNDS (4 >= 0)...
PRE-SIM FAIL fulfill_condition: 🛑 INDEX OUT OF BOUNDS (4 >= 0)
[2498] fulfill_condition_PRECHECK_FAIL → ❌ 📏 🛑 INDEX OUT OF BOUNDS (0 >= 0)...      
PRE-SIM FAIL fulfill_condition: 🛑 INDEX OUT OF BOUNDS (0 >= 0)
[2499] fulfill_condition_PRECHECK_FAIL → ❌ 📏 🛑 INDEX OUT OF BOUNDS (0 >= 0)...
PRE-SIM FAIL fulfill_condition: 🛑 INDEX OUT OF BOUNDS (0 >= 0)
[2500] refund_PRECHECK_FAIL → ❌ 💰 🛑 NOT FUNDED (State≠1)...
PRE-SIM FAIL refund: 🛑 NOT FUNDED (State≠1)
[2501] deposit_eth → ✅ 🌐 
✅ deposit_eth succeeded
[2502] release_PRECHECK_FAIL → ❌ 💰 🛑 NOT FUNDED (State≠1)...
PRE-SIM FAIL release: 🛑 NOT FUNDED (State≠1)
[2503] deposit_eth → ❌ 🌐 🛑 UNKNOWN CV REVERT...
❌ deposit_eth TX REVERTED: 🛑 UNKNOWN CV REVERT
[2504] deposit_eth → ❌ 🌐 🛑 UNKNOWN CV REVERT...
❌ deposit_eth TX REVERTED: 🛑 UNKNOWN CV REVERT
📊 Iteration success rate: 20.0%
=== Iteration complete ===

✅ Saved 2505 results to fuzz_results_20251215_162506.json</code></pre>
