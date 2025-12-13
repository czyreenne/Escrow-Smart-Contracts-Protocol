# pragma version 0.4.3
'''
@license MIT
@title Condition Verifier Contract
@notice Verifies various types of conditions for escrow automation
@dev Supports ETH deposits and can be extended for NFT/token transfers
'''

# NEW: Flag for condition types (replaces deprecated enum)
flag ConditionType:
    ETH_DEPOSIT # 1
    # NFT_TRANSFER # 2, Placeholder for future implementation
    # TOKEN_TRANSFER # 4, Placeholder for future implementation

# Events for transparency
event ConditionCreated:
    condition_id: uint256
    condition_type: ConditionType
    creator: address
    beneficiary: address
    timestamp: uint256

event EthDepositReceived:
    condition_id: uint256
    depositor: address
    amount: uint256
    timestamp: uint256

event EthForwarded:
    condition_id: uint256
    beneficiary: address
    amount: uint256
    timestamp: uint256

event ConditionFulfilled:
    condition_id: uint256
    condition_type: ConditionType
    timestamp: uint256

event DisputeRaised:
    condition_id: uint256
    disputer: address
    reason: String[200]

# Struct to track each condition
struct Condition:
    condition_type: ConditionType
    creator: address  # Usually the seller who creates the condition
    beneficiary: address  # Third-party who should receive funds/assets
    required_amount: uint256  # For ETH_DEPOSIT: minimum amount required
    received_amount: uint256  # Actual amount received
    fulfilled: bool
    disputed: bool
    created_at: uint256
    fulfilled_at: uint256

# Storage
conditions: public(HashMap[uint256, Condition])
condition_count: public(uint256)
owner: public(address)

@deploy
def __init__():
    self.owner = msg.sender
    self.condition_count = 0

# Create a new ETH deposit condition
@external
def create_eth_deposit_condition(
    beneficiary: address,
    required_amount: uint256
) -> uint256:
    """
    Creates a new ETH deposit condition
    Returns the condition_id for tracking
    """
    assert beneficiary != empty(address), "Invalid beneficiary address"
    assert required_amount > 0, "Required amount must be positive"
    
    condition_id: uint256 = self.condition_count
    
    self.conditions[condition_id] = Condition(
        condition_type=ConditionType.ETH_DEPOSIT,
        creator=msg.sender,
        beneficiary=beneficiary,
        required_amount=required_amount,
        received_amount=0,
        fulfilled=False,
        disputed=False,
        created_at=block.timestamp,
        fulfilled_at=0
    )
    
    self.condition_count += 1
    
    log ConditionCreated(
        condition_id=condition_id,
        condition_type=ConditionType.ETH_DEPOSIT,
        creator=msg.sender,
        beneficiary=beneficiary,
        timestamp=block.timestamp
    )
    
    return condition_id

# Deposit ETH for a specific condition
@external
@payable
def deposit_eth(condition_id: uint256):
    """
    Allows anyone to deposit ETH for a specific condition
    Automatically forwards to beneficiary and marks as fulfilled if amount met
    """
    assert condition_id < self.condition_count, "Invalid condition ID"
    assert msg.value > 0, "Must send ETH"
    
    condition: Condition = self.conditions[condition_id]
    assert condition.condition_type == ConditionType.ETH_DEPOSIT, "Not an ETH deposit condition"
    assert not condition.fulfilled, "Condition already fulfilled"
    assert not condition.disputed, "Condition is disputed"
    
    # Update received amount
    self.conditions[condition_id].received_amount += msg.value
    
    log EthDepositReceived(
        condition_id=condition_id,
        depositor=msg.sender,
        amount=msg.value,
        timestamp=block.timestamp
    )
    
    # Forward ETH to beneficiary immediately
    send(condition.beneficiary, msg.value)
    
    log EthForwarded(
        condition_id=condition_id,
        beneficiary=condition.beneficiary,
        amount=msg.value,
        timestamp=block.timestamp
    )
    
    # Check if required amount has been met
    if self.conditions[condition_id].received_amount >= condition.required_amount:
        self.conditions[condition_id].fulfilled = True
        self.conditions[condition_id].fulfilled_at = block.timestamp
        
        log ConditionFulfilled(
            condition_id=condition_id,
            condition_type=ConditionType.ETH_DEPOSIT,
            timestamp=block.timestamp
        )

# Raise a dispute (only creator or beneficiary can dispute)
@external
def raise_dispute(condition_id: uint256, reason: String[200]):
    assert condition_id < self.condition_count, "Invalid condition ID"
    condition: Condition = self.conditions[condition_id]
    
    assert msg.sender == condition.creator or msg.sender == condition.beneficiary, \
        "Only creator or beneficiary can dispute"
    assert not condition.fulfilled, "Cannot dispute fulfilled condition"
    
    self.conditions[condition_id].disputed = True
    
    log DisputeRaised(
        condition_id=condition_id,
        disputer=msg.sender,
        reason=reason
    )

# VIEW FUNCTIONS - Can be called via staticcall from Escrow contract

@external
@view
def is_condition_fulfilled(condition_id: uint256) -> bool:
    """Check if condition is fulfilled and not disputed"""
    if condition_id >= self.condition_count:
        return False
    condition: Condition = self.conditions[condition_id]
    return condition.fulfilled and not condition.disputed

@external
@view
def get_condition_status(condition_id: uint256) -> (bool, bool, uint256, uint256):
    """Returns (fulfilled, disputed, required_amount, received_amount)"""
    assert condition_id < self.condition_count, "Invalid condition ID"
    condition: Condition = self.conditions[condition_id]
    return (
        condition.fulfilled,
        condition.disputed,
        condition.required_amount,
        condition.received_amount
    )

@external
@view
def get_condition_details(condition_id: uint256) -> (
    ConditionType,  # Return the enum type directly, not uint8
    address,  # creator
    address,  # beneficiary
    uint256,  # required_amount
    uint256,  # received_amount
    bool,  # fulfilled
    bool,  # disputed
    uint256,  # created_at
    uint256   # fulfilled_at
):
    """Returns full condition details"""
    assert condition_id < self.condition_count, "Invalid condition ID"
    condition: Condition = self.conditions[condition_id]
    return (
        condition.condition_type,  # Return as ConditionType enum
        condition.creator,
        condition.beneficiary,
        condition.required_amount,
        condition.received_amount,
        condition.fulfilled,
        condition.disputed,
        condition.created_at,
        condition.fulfilled_at
    )

@external
@view
def verify_condition_for_parties(
    condition_id: uint256,
    expected_creator: address,
    expected_beneficiary: address
) -> bool:
    """Verify condition is fulfilled for specific creator/beneficiary pair"""
    if condition_id >= self.condition_count:
        return False
    
    condition: Condition = self.conditions[condition_id]
    return (
        condition.fulfilled and
        not condition.disputed and
        condition.creator == expected_creator and
        condition.beneficiary == expected_beneficiary
    )
