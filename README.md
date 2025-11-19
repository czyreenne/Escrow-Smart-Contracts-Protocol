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
4. Install dependencies in virtual environment (`pip install vyper` and set up web3 `pip show web3`)
5. Check that Vyper (`vyper --version`) and Web3 (`web3 --version`) are installed 
6. [Guide to deploy and test](docs/overview.md)
7. Compile Escrow.vy script and get abi (`vyper -f abi Escrow.vy`) and bytecode (`vyper -f bytecode Escrow.vy`). Make sure you are in the same directory as Escrow.vy script or replace Escrow.vy to path to file Escrow.vy.
8. Set deployer private key as an environment variable (For PS terminals -> `$Env:DEPLOYER_PRIVATE_KEY="0xYOUR_PRIVATE_KEY"`)
9. Input seller address when deploying (`python deploy.py 0xSELLER_ADDRESS`)

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
