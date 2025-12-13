"""
Keeper Bot for Escrow Automation
Monitors ConditionVerifier for ConditionFulfilled events
Automatically calls release() on linked Escrow contracts
"""

import os
import sys
import json
import time
from web3 import Web3
from datetime import datetime
import getpass

# Configuration
GANACHE_URL = "http://127.0.0.1:8545"
POLL_INTERVAL = 5  # seconds between checks
DEPLOYMENTS_PATH = "deployments/testnet.json"

class EscrowKeeperBot:
    def __init__(self, seller_private_key):
        """Initialize the keeper bot with Web3 connection and contract interfaces"""
        self.w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
        assert self.w3.is_connected(), "Failed to connect to Ganache!"
        
        # Set up seller account (who will call release())
        self.seller_account = self.w3.eth.account.from_key(seller_private_key)
        self.seller_address = self.seller_account.address
        print(f"Keeper bot initialized for seller: {self.seller_address}")
        
        # Load deployment data
        self.deployments = self._load_deployments()
        
        # Track which conditions we've already processed
        self.processed_conditions = set()
        
        # Event filters
        self.filters = {}
        
    def _load_deployments(self):
        """Load deployment data from testnet.json"""
        if not os.path.exists(DEPLOYMENTS_PATH):
            raise FileNotFoundError(f"Deployment file not found: {DEPLOYMENTS_PATH}")
        
        with open(DEPLOYMENTS_PATH, 'r') as f:
            data = json.load(f)
        
        # Extract contract addresses and ABIs
        deployments = {
            'escrow_contracts': [],
            'condition_verifier': None
        }
        
        for deployment in data.get('deployments', []):
            if deployment['contract'] == 'ConditionVerifier':
                deployments['condition_verifier'] = {
                    'address': deployment['address'],
                    'abi': self._load_abi('contracts/ConditionVerifier.abi')
                }
            elif deployment['contract'] == 'Escrow':
                deployments['escrow_contracts'].append({
                    'address': deployment['address'],
                    'seller': deployment['seller'],
                    'condition_id': deployment['linkedContracts']['externalConditionId'],
                    'condition_verifier': deployment['linkedContracts']['conditionVerifier'],
                    'abi': self._load_abi('contracts/Escrow.abi')
                })
        
        print(f"\nLoaded {len(deployments['escrow_contracts'])} escrow contract(s)")
        if deployments['condition_verifier']:
            print(f"ConditionVerifier: {deployments['condition_verifier']['address']}")
        
        return deployments
    
    def _load_abi(self, path):
        """Load ABI from file"""
        with open(path, 'r') as f:
            return json.load(f)
    
    def setup_event_filters(self):
        """Set up event filters for monitoring"""
        cv_address = self.deployments['condition_verifier']['address']
        cv_abi = self.deployments['condition_verifier']['abi']
        
        # Create contract instance
        cv_contract = self.w3.eth.contract(address=cv_address, abi=cv_abi)
        
        # Filter for ConditionFulfilled events
        # Changed: fromBlock -> from_block
        self.filters['condition_fulfilled'] = cv_contract.events.ConditionFulfilled.create_filter(
            from_block='latest'  # ← Changed from fromBlock
        )
        
        print(f"\n✓ Event filters set up")
        print(f"  Monitoring: ConditionFulfilled events from {cv_address}")

    def check_new_fulfilled_conditions(self):
        """Check for new ConditionFulfilled events"""
        try:
            events = self.filters['condition_fulfilled'].get_new_entries()
            
            for event in events:
                condition_id = event['args']['condition_id']
                
                # Skip if already processed
                if condition_id in self.processed_conditions:
                    continue
                
                print(f"\n🔔 NEW EVENT: ConditionFulfilled")
                print(f"   Condition ID: {condition_id}")
                print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Find matching escrow contract(s)
                matching_escrows = [
                    escrow for escrow in self.deployments['escrow_contracts']
                    if escrow['condition_id'] == condition_id
                ]
                
                if matching_escrows:
                    for escrow in matching_escrows:
                        self.attempt_release(escrow, condition_id)
                else:
                    print(f"   ⚠️  No matching escrow found for condition {condition_id}")
                
                # Mark as processed
                self.processed_conditions.add(condition_id)
                
        except Exception as e:
            print(f"Error checking events: {e}")
    
    def attempt_release(self, escrow_data, condition_id):
        """Attempt to call release() on an escrow contract"""
        escrow_address = escrow_data['address']
        escrow_seller = escrow_data['seller']
        
        print(f"\n🤖 ATTEMPTING AUTO-RELEASE")
        print(f"   Escrow: {escrow_address}")
        print(f"   Seller: {escrow_seller}")
        
        # Verify this bot controls the seller account
        if self.seller_address.lower() != escrow_seller.lower():
            print(f"   ❌ Bot account mismatch!")
            print(f"      Bot: {self.seller_address}")
            print(f"      Required: {escrow_seller}")
            return
        
        # Create escrow contract instance
        escrow_contract = self.w3.eth.contract(
            address=escrow_address,
            abi=escrow_data['abi']
        )
        
        try:
            # Check escrow state before attempting release
            state = escrow_contract.functions.state().call()
            if state != 1:
                print(f"   ⚠️  Escrow not funded (state={state})")
                return
            
            # Pre-check: simulate the call
            try:
                escrow_contract.functions.release().call({'from': self.seller_address})
                print(f"   ✓ Pre-check passed")
            except Exception as sim_error:
                print(f"   ❌ Pre-check failed: {sim_error}")
                return
            
            # Build release transaction
            nonce = self.w3.eth.get_transaction_count(self.seller_address)
            
            release_tx = escrow_contract.functions.release().build_transaction({
                'from': self.seller_address,
                'nonce': nonce,
                'gas': 500000,
                'gasPrice': self.w3.to_wei('20', 'gwei')
            })
            
            # Sign and send transaction (for integrity)
            signed_tx = self.w3.eth.account.sign_transaction(
                release_tx,
                private_key=self.seller_account.key
            )
            
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"   📤 Release TX sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                # Get released amount from events
                try:
                    released_events = escrow_contract.events.Released().process_receipt(receipt)
                    if released_events:
                        amount = released_events[0]['args']['amount']
                        print(f"   ✅ RELEASE SUCCESSFUL!")
                        print(f"      Amount: {self.w3.from_wei(amount, 'ether')} ETH")
                        print(f"      Gas used: {receipt.gasUsed}")
                    else:
                        print(f"   ✅ Transaction successful (status=1)")
                except:
                    print(f"   ✅ Transaction successful (status=1)")
            else:
                print(f"   ❌ Release failed (status=0)")
                print(f"      TX: {tx_hash.hex()}")
                
        except Exception as e:
            print(f"   ❌ Error during release: {e}")
    
    def run(self):
        """Main bot loop"""
        print("\n" + "="*60)
        print("🤖 ESCROW KEEPER BOT STARTED")
        print("="*60)
        print(f"Polling interval: {POLL_INTERVAL} seconds")
        print(f"Press Ctrl+C to stop")
        print("="*60)
        
        # Set up event monitoring
        self.setup_event_filters()
        
        try:
            while True:
                self.check_new_fulfilled_conditions()
                time.sleep(POLL_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Bot stopped by user")
            print("="*60)
        except Exception as e:
            print(f"\n\n❌ Bot crashed: {e}")
            raise


def main():
    """Entry point for keeper bot"""
    print("="*60)
    print("ESCROW KEEPER BOT INITIALIZATION")
    print("="*60)
    
    # Get seller private key
    seller_key = getpass.getpass(prompt="Enter seller private key: ")
    
    if not seller_key:
        print("Error: Private key required")
        sys.exit(1)
    
    # Initialize and run bot
    bot = EscrowKeeperBot(seller_key)
    bot.run()


if __name__ == "__main__":
    main()
