# Protocol Overview

## What is this?
An open-source escrow contract protocol targeting real-world legal/commercial usability—implemented in Vyper, securely tested, and deployable on Sepolia.

## Key Concepts
- **Participants:** Buyer, Seller, (optional) Arbitrator
- **Workflow:** Buyer deposits → Seller fulfills contract → Funds released or timeout triggers refund

## Example Workflow
1. Buyer deploys contract specifying seller and timeout.
2. Buyer deposits funds.
3. Seller calls release to withdraw, OR
4. If timeout passes, buyer can refund.

## Key Security Features
- No modifiers or inheritance for clarity and safety
- Explicit state machines
- Event logs for all important actions

Refer to [architecture-diagram.png](architecture-diagram.png) for a visual summary.
