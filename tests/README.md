## Test Directory Structure
The testing suite consists of the following files:
- `test_deploy.py`: Deploys ConditionVerifier and Escrow contracts without requiring manual input of the deployer's private key, allowing for multiple contract redeployments quickly to simulate a clean room environment. 
- `test_escrow.py`: Runs seventeen manually drafted edge cases, deploying a fresh contract for each case
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
7. ZERO CONDITIONS           → release: SUCCESS; refund: FAIL (external only)
8. EMPTY DESCRIPTION         → SUCCESS (no restrictions)

9-13. PERMISSION TESTS       → FAIL (attempting operations as wrong roles)
14. DEPOSIT ZERO VALUE       → FAIL (cannot deposit 0 value)
15. RELEASE NOT FUNDED       → FAIL (cannot release unfunded contract)
16. RELEASE ONLY INTERNAL    → FAIL (only release when both internal and external are fulfilled) 
17. REFUND NOT FUNDED        → FAIL (cannot refund unfunded contract)
18. REFUND ONLY INTERNAL     → SUCCESS (can refund as long as internal/external has not been completed)
19. REFUND ONLY EXTERNAL     → SUCCESS (can refund as long as internal/external has not been completed)

## Sample Output for tests/test_escrow.py
First manual test in test_escrow.py output [Double Deposit -> second deposit should fail]:
<pre><code>
---TEST 1: Repeated Deposit---
ConditionVerifier deployed at: 0x33a71218f69AFF41379C0e090A8016CEEe5c9aFC
Condition created with ID: 0
Escrow deployed at: 0x4fC46B7f8f2812330f5847aB6f880117f3c018B7

💰 Testing repeated deposit...
EXPECTED RESULT:❌ FAIL - contract has already been funded.

=== Attempting First Deposit ===
✅ DEPOSIT SUCCEEDED!
=== Attempting Second Deposit ===
❌ DEPOSIT FAILED: TX REVERTED (status=0)</code></pre>

Another manual test in test_escrow.py output [Partial Completion of Conditions -> release of funds should fail]
<pre><code>---TEST 6: Partial Internal Condition Fulfilment Release---
ConditionVerifier deployed at: 0x18B19D1806f889B188D73629d82128b1B9D7cE65
Condition created with ID: 0
Escrow deployed at: 0x3691AaBc1872f7367D2544D17886fb35144739AE

🏃 Testing Release while fulfilling only some Conditions...
EXPECTED RESULT:❌ FAIL - cannot release funds with partial completion.

===Attempting Deposit===
✅ DEPOSIT SUCCEEDED!
===Attempting to add condition 0===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 1===
✅ Condition ADDED: 'Random condition'

===Completing First Condition===
✅ Condition 0 FULFILLED ✓
===Fulfilling external condition===
✅ Deposited to ConditionVerifier for condition 0
✅ External condition FULFILLED!
===Attempting Early Release===
❌ RELEASE FAILED: TX REVERTED (status=0)

Condition check:❌ Not all conditions are fulfilled.
===Checking conditions===
📋 Total Conditions: 2
  ✅ [0] Random condition
  ❌ [1] Random condition</code></pre>

All tests in test_escrow.py output:
<pre><code>---TESTS BEGIN NOW---

---TEST 1: Repeated Deposit---
ConditionVerifier deployed at: 0x33a71218f69AFF41379C0e090A8016CEEe5c9aFC
Condition created with ID: 0
Escrow deployed at: 0x4fC46B7f8f2812330f5847aB6f880117f3c018B7

💰 Testing repeated deposit...
EXPECTED RESULT:❌ FAIL - contract has already been funded.

=== Attempting First Deposit ===
✅ DEPOSIT SUCCEEDED!
=== Attempting Second Deposit ===
❌ DEPOSIT FAILED: TX REVERTED (status=0)
---------------------------------------------------------------------------------
---TEST 2: Release Before Internal Condition Fulfilment---
ConditionVerifier deployed at: 0x624f161B1E1CCd255aa2A0C7406d651EA583b8E2
Condition created with ID: 0
Escrow deployed at: 0x14579fAb6e52A781972a8117424bd8c69b9d9D63

🏃 Testing early release (0 completions)...
EXPECTED RESULT:❌ FAIL - internal condition not fulfilled.

===Attempting deposit===
✅ DEPOSIT SUCCEEDED!
===Attempting to add a simple condition===
✅ Condition ADDED: 'Random condition'
===Fulfilling external condition===
✅ Deposited to ConditionVerifier for condition 0
✅ External condition FULFILLED!
===Attempting to perform early release===
❌ RELEASE FAILED: TX REVERTED (status=0)

Condition check:❌ Not all conditions are fulfilled.
---------------------------------------------------------------------------------
---TEST 3A: Edge Timeout---
ConditionVerifier deployed at: 0x2f4cB70b1B9444301ff6a02DF7192CE2d627786c
Condition created with ID: 0
Escrow deployed at: 0xAed1900adCFC19B7f9aAf37297d633C92Efb22AA

⏱️ Testing edge timeout: Before Timeout...
EXPECTED RESULT:❌ FAIL - not enough time has passed to request a refund.

===Attempting deposit===
✅ DEPOSIT SUCCEEDED!
===Attempting to add a simple condition===
✅ Condition ADDED: 'Random condition'
===Fulfilling external condition===
✅ Deposited to ConditionVerifier for condition 0
✅ External condition FULFILLED!
===Fastforwarding and attempting refund by 3599 (current timeout: 3600)===
⏩ Time advanced
❌ REFUND FAILED: TX REVERTED (status=0)

Condition check:❌ Not all conditions are fulfilled.

---TEST 3B: Edge Timeout---
ConditionVerifier deployed at: 0x04264ecc885EAa905a3946848e9fa8431a385fF3
Condition created with ID: 0
Escrow deployed at: 0xA0672b6b070E0C4e7d99bC1D62069CdbF371f642

⏱️ Testing edge timeout: Exactly on Timeout...
EXPECTED RESULT:❌ FAIL - buyer can only request refund AFTER timeout

===Attempting deposit===
✅ DEPOSIT SUCCEEDED!
===Attempting to add a simple condition===
✅ Condition ADDED: 'Random condition'
===Fulfilling external condition===
✅ Deposited to ConditionVerifier for condition 0
✅ External condition FULFILLED!
===Fastforwarding and attempting refund by 3600===
⏩ Time advanced
❌ REFUND FAILED: TX REVERTED (status=0)

Condition check:❌ Not all conditions are fulfilled.

---TEST 3C: Edge Timeout---
ConditionVerifier deployed at: 0xe2acc3D7AED21627B5fb960B1f678b2BEe6179dB
Condition created with ID: 0
Escrow deployed at: 0xa4575Fc359f0e14a82722253fB0C8335190a8F19

⏱️ Testing edge timeout: Just after timeout...
EXPECTED RESULT:✅ SUCCESS - enough time has passed

===Attempting deposit===
✅ DEPOSIT SUCCEEDED!
===Attempting to add a simple condition===
✅ Condition ADDED: 'Random condition'
===Fulfilling external condition===
✅ Deposited to ConditionVerifier for condition 0
✅ External condition FULFILLED!
===Fastforwarding and attempting refund by just over 3600===
⏩ Time advanced past timeout
✅ REFUND SUCCEEDED!
---------------------------------------------------------------------------------
---TEST 4: Refund after Condition Completion---
ConditionVerifier deployed at: 0x1bf2c9A9F538B7c33Aeb4f2Ca54E57fa0A9f4FD6
Condition created with ID: 0
Escrow deployed at: 0xF53E6212Ba5ef741813924D47B0EC246F3Bd51bE

🔙 Testing Refund after Completing All Conditions...
EXPECTED RESULT:❌ FAIL - buyer cannot request refund after seller has completed conditions

===Attempting deposit===
✅ DEPOSIT SUCCEEDED!
===Attempting to add a simple condition===
✅ Condition ADDED: 'Random condition'
===Completing Condition===
✅ Condition 0 FULFILLED ✓
===Fulfilling external condition===
✅ Deposited to ConditionVerifier for condition 0
✅ External condition FULFILLED!
===Fastforwarding and attempting refund by just over 3600===
⏩ Time advanced past timeout
❌ REFUND FAILED: TX REVERTED (status=0)

Condition check:✅ All conditions are fulfilled
---------------------------------------------------------------------------------
---TEST 5: Invalid Internal Condition Index---
ConditionVerifier deployed at: 0xaa9256b40A2b1805c8182A6D9199333c09989779
Condition created with ID: 0
Escrow deployed at: 0xaC329391815C391276876C4040863C62Acf24f1b

☝️ Testing Invalid Condition Index + Max Conditions + Double Completion
This first part tests if we can add an 11th condition and complete it.
EXPECTED RESULT:❌ FAIL - maximum 10 internal conditions

===Attempting Deposit===
✅ DEPOSIT SUCCEEDED!

===Attempting to add condition 0===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 1===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 2===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 3===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 4===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 5===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 6===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 7===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 8===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 9===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 10===
❌ add_conditions FAILED: TX REVERTED (status=0)

===Completing Condition outside of Index===
❌ fulfill_condition(10) FAILED: TX REVERTED (status=0)
===Checking conditions===
📋 Total Conditions: 10
  ❌ [0] Random condition
  ❌ [1] Random condition
  ❌ [2] Random condition
  ❌ [3] Random condition
  ❌ [4] Random condition
  ❌ [5] Random condition
  ❌ [6] Random condition
  ❌ [7] Random condition
  ❌ [8] Random condition
  ❌ [9] Random condition

📝 This second part now tests if we can fulfill all 10 internal conditions and release funds.
EXPECTED RESULT:✅ SUCCESS - fulfilling all conditions should allow release.

===Completing all 10 Conditions===
✅ Condition 0 FULFILLED ✓
✅ Condition 1 FULFILLED ✓
✅ Condition 2 FULFILLED ✓
✅ Condition 3 FULFILLED ✓
✅ Condition 4 FULFILLED ✓
✅ Condition 5 FULFILLED ✓
✅ Condition 6 FULFILLED ✓
✅ Condition 7 FULFILLED ✓
✅ Condition 8 FULFILLED ✓
✅ Condition 9 FULFILLED ✓
===Fulfilling external condition===
✅ Deposited to ConditionVerifier for condition 0
✅ External condition FULFILLED!
===Attempting Release===
✅ RELEASE SUCCEEDED! 🎉!
===Checking conditions===
📋 Total Conditions: 10
  ✅ [0] Random condition
  ✅ [1] Random condition
  ✅ [2] Random condition
  ✅ [3] Random condition
  ✅ [4] Random condition
  ✅ [5] Random condition
  ✅ [6] Random condition
  ✅ [7] Random condition
  ✅ [8] Random condition
  ✅ [9] Random condition

🤔 This third part tests what happens if we attempt to fulfill the same condition twice
EXPECTED RESULT:❌ FAIL - Condition has already been fulfilled.

===Completing the first Condition again===
❌ fulfill_condition(0) FAILED: TX REVERTED (status=0)
---------------------------------------------------------------------------------
---TEST 6: Partial Internal Condition Fulfilment Release---
ConditionVerifier deployed at: 0x18B19D1806f889B188D73629d82128b1B9D7cE65
Condition created with ID: 0
Escrow deployed at: 0x3691AaBc1872f7367D2544D17886fb35144739AE

🏃 Testing Release while fulfilling only some Conditions...
EXPECTED RESULT:❌ FAIL - cannot release funds with partial completion.

===Attempting Deposit===
✅ DEPOSIT SUCCEEDED!
===Attempting to add condition 0===
✅ Condition ADDED: 'Random condition'
===Attempting to add condition 1===
✅ Condition ADDED: 'Random condition'

===Completing First Condition===
✅ Condition 0 FULFILLED ✓
===Fulfilling external condition===
✅ Deposited to ConditionVerifier for condition 0
✅ External condition FULFILLED!
===Attempting Early Release===
❌ RELEASE FAILED: TX REVERTED (status=0)

Condition check:❌ Not all conditions are fulfilled.
===Checking conditions===
📋 Total Conditions: 2
  ✅ [0] Random condition
  ❌ [1] Random condition
---------------------------------------------------------------------------------
---TEST 7A: Zero Internal Conditions Release---
ConditionVerifier deployed at: 0x5eD07928b6C85B8705E9c7EfCbEF78006Cc96e4c
Condition created with ID: 0
Escrow deployed at: 0x6A47D99323AF9865a14cefEA260C5b2Bbf5c3aAb

0️⃣ Testing Release with 0 internal conditions...
EXPECTED RESULT:✅ SUCCESS - once the external condition is fulfilled, it should release.

===Attempting Deposit===
✅ DEPOSIT SUCCEEDED!
===Fulfilling external condition===
✅ Deposited to ConditionVerifier for condition 0
✅ External condition FULFILLED!
===Attempting Release===
✅ RELEASE SUCCEEDED! 🎉!

---TEST 7B: Zero Internal Conditions Refund---
ConditionVerifier deployed at: 0xeB076b9A7B460717Bf39B7dc2DcD096Ab07215b5
Condition created with ID: 0
Escrow deployed at: 0xA352f70fb7f5f93079EebAe64BeA35a63DDAe4f0

0️⃣ Testing Refund with 0 internal conditions...
EXPECTED RESULT:❌ FAIL - once the external condition is fulfilled, refund is no longer permitted.

===Attempting Deposit===
✅ DEPOSIT SUCCEEDED!
===Fulfilling external condition===
✅ Deposited to ConditionVerifier for condition 0
✅ External condition FULFILLED!
===Attempting Refund===
⏩ Time advanced past timeout
❌ REFUND FAILED: TX REVERTED (status=0)

Condition check:✅ All conditions are fulfilled
---------------------------------------------------------------------------------
---TEST 8: Empty Internal Condition Description---
ConditionVerifier deployed at: 0xD0B2B45beA683d795d2f6d7A1498A95e1Ad14f69
Condition created with ID: 0
Escrow deployed at: 0xF5d03EFd3423521CF1178790797ECf0052231E4D

☁️ Testing adding internal condition with empty description...
EXPECTED RESULT:✅ SUCCESS - no restriction on condition description.

===Adding Condition with no Description===
✅ Condition ADDED: ''
===Checking Conditions===
📋 Total Conditions: 1
  ❌ [0]</code></pre>

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

## Coverage Table:
**Core Workflow**: See main README
| Test | Description | In |
| --- | --- | --- |
| successful_deployment | Deploy contract, verify internal state | interact.py |
| successful_deposit | Buyer deposits funds successfully | interact.py |
| add_single_condition | Buyer adds one internal condition | interact.py |
| fulfill_single_condition | Seller fulfills an internal condition | interact.py |
| successful_release_with_internal_conditions | *Full flow*: deposit -> add conditions -> fulfill conditions -> deposit_to_verifier -> release | interact.py |
| successful_refund_timeout | Deposit -> add conditions -> wait for timeout -> refund | interact.py |

**Edge Cases surrounding Permissions**: See test_escrow.py
| Test | Description | In |
| --- | --- | --- |
| failed_deposit_wrong_sender | Non-buyer tries to deposit | Test 9 test_escrow.py |
| add_condition_non_buyer | Non-buyer tries to add an internal condition | Test 10 test_escrow.py |
| fulfill_condition_non_seller | Non-seller tries to fulfill an internal condition | Test 11 test_escrow.py |
| release_non_seller | Non-seller tries to release | Test 12 test_escrow.py |
| refund_non_buyer | Non-buyer tries to refund | Test 13 test_escrow.py |

**Edge Cases surrounding Deposit Function**: See test_escrow.py
| Test | Description | In |
| --- | --- | --- |
| failed_double_deposit | Buyer deposits funds twice | Test 1 test_escrow.py |
| failed_deposit_zero_value | Try depositing 0 wei | Test 14 test_escrow.py |

**Edge Cases surrounding Add Conditions Function**: See test_escrow.py
| Test | Description | In |
| --- | --- | --- |
| add_max_conditions | Add 10 conditions successfully | Test 5 test_escrow.py |
| exceed_max_conditions | Add an 11th condition (should fail) | Test 5 test_escrow.py |
| add_empty_description | Add a condition with an empty string for the description | Test 8 test_escrow.py |

**Edge Cases surrounding Fulfill Conditions Function**: See test_escrow.py
| Test | Description | In |
| --- | --- | --- |
| fulfill_invalid_index | Try to fulfill condition index >= num_conditions | Test 5 test_escrow.py |
| fulfill_already_fulfilled | Try to fulfill the same condition twice | Test 5 test_escrow.py |

**Edge Cases surrounding Release Function**: See test_escrow.py
| Test | Description | In |
| --- | --- | --- |
| early_release | Internal conditions partially completed / not completed at all | Tests 2, 6 test_escrow.py |
| successful_release_no_internal_conditions | Deposit -> deposit_to_verifier -> release | Test 7A test_escrow.py | 
| release_not_funded | Release before deposit | Test 15 test_escrow.py | 
| early_release_external |  External condition not fulfilled | Test 16 test_escrow.py | 


**Edge Cases surrounding Refund Function**: See test_escrow.py
| Test | Description | In |
| --- | --- | --- |
| refund_before_timeout | Refund just before timeout expires | Test 3A test_escrow.py |
| refund_exactly_at_timeout | Refund exactly at timeout | Test 3B test_escrow.py |
| refund_after_completion | Try refund when both internal and external conditions are fulfilled | Test 4 test_escrow.py |
| refund_before_deposit | Refund before deposit | Test 17 test_escrow.py |
| refund_only_internal | Internal conditions fulfilled, external not fulfilled | Test 18 test_escrow.py |
| refund_only_external | Internal conditions not fulfilled, external fulfilled | Test 19 test_escrow.py |


