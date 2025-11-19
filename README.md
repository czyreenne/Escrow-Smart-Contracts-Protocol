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
3. On another terminal, set deployer private key as one of the private keys available(`$Env:DEPLOYER_PRIVATE_KEY="0x4b7ebe9e5c43116f7a8366d8f30302de1ab46fe488daa8aafa6b5c96f8adc523"`)
4. Run deploy.py (`python scripts/deploy.py 0x3bb560C961616430c4f1974243c6a3c0E99B129f`). Note: Seller address should belong to a different test account than the private key test account.
5. 

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
