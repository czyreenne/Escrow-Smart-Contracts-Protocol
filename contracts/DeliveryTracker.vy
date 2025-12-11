# pragma version 0.4.3
'''
@ license MIT
@ title Delivery Tracker Contract

@ notice External contract that tracks delivery status for escrow condition verification
'''

# Events for transparency
event DeliveryInitiated:
    tracking_id: uint256
    seller: address
    buyer: address
    timestamp: uint256

event DeliveryConfirmed:
    tracking_id: uint256
    confirmer: address
    timestamp: uint256

event DisputeRaised:
    tracking_id: uint256
    disputer: address
    reason: String[200]

struct Delivery:
    seller: address
    buyer: address
    initiated: bool
    confirmed: bool
    disputed: bool
    initiation_time: uint256
    confirmation_time: uint256
    metadata: String[200]                               # Optional delivery details

deliveries: public(HashMap[uint256, Delivery])
authorized_confirmers: public(HashMap[address, bool])   # Couriers, delivery services
owner: public(address)

@deploy
def __init__():
    self.owner = msg.sender

@external
def authorize_confirmer(confirmer: address):
    assert msg.sender == self.owner, "Only owner can authorize confirmers!"
    self.authorized_confirmers[confirmer] = True

@external
def revoke_confirmer(confirmer: address):
    assert msg.sender == self.owner, "Only owner can revoke confirmers!"
    self.authorized_confirmers[confirmer] = False

# Seller initiates delivery tracking
@external
def initiate_delivery(tracking_id: uint256, buyer: address, metadata: String[200]):
    assert not self.deliveries[tracking_id].initiated, "Tracking ID already exists!"
    assert buyer != empty(address), "Invalid buyer address"

    self.deliveries[tracking_id] = Delivery(
        seller = msg.sender,
        buyer = buyer,
        initiated = True,
        confirmed = False,
        disputed = False,
        initiation_time = block.timestamp,
        confirmation_time = 0,
        metadata = metadata
    )

    log DeliveryInitiated(
        tracking_id = tracking_id, 
        seller = msg.sender,
        buyer = buyer,
        timestamp = block.timestamp
    )

# Buyer OR authorized confirmer can confirm delivery
@external
def confirm_delivery(tracking_id: uint256):
    assert self.deliveries[tracking_id].initiated, "Delivery not initiated!"
    assert not self.deliveries[tracking_id].confirmed, "Already confirmed"
    assert not self.deliveries[tracking_id].disputed, "Delivery is disputed"

    # Allow buyer or authorized confirmer to confirm
    delivery: Delivery = self.deliveries[tracking_id]
    assert (msg.sender == delivery.buyer) or self.authorized_confirmers[msg.sender], "Only buyer or authorized confirmer can confirm!"

    self.deliveries[tracking_id].confirmed = True
    self.deliveries[tracking_id].confirmation_time = block.timestamp

    log DeliveryConfirmed(
        tracking_id = tracking_id,
        confirmer = msg.sender,
        timestamp = block.timestamp
    )

# Buyer can raise a dispute
@external
def raise_dispute(tracking_id: uint256, reason: String[200]):
    assert self.deliveries[tracking_id].initiated, "Delivery not initiated"
    delivery: Delivery = self.deliveries[tracking_id]
    assert msg.sender == delivery.buyer, "Only buyer can dispute"
    assert not delivery.confirmed, "Cannot dispute confirmed delivery"
    
    self.deliveries[tracking_id].disputed = True
    
    log DisputeRaised(
        tracking_id=tracking_id,
        disputer=msg.sender,
        reason=reason
    )

# View Functions - Can be called via staticcall from the Escrow contract

@external
@view
def is_delivery_confirmed(tracking_id: uint256) -> bool:
    '''Takes in delivery tracking id and returns true if delivery is confirmed and undisputed'''
    return self.deliveries[tracking_id].confirmed and not self.deliveries[tracking_id].disputed

@external
@view
def get_delivery_status(tracking_id: uint256) -> (bool, bool, bool):
    '''Returns initiated, confirmed, disputed '''
    delivery: Delivery = self.deliveries[tracking_id]
    return (delivery.initiated, delivery.confirmed, delivery.disputed)

@external
@view
def get_delivery_details(tracking_id: uint256) -> (address, address, uint256, uint256, String[200]):
    """Returns full delivery details"""
    delivery: Delivery = self.deliveries[tracking_id]
    return (
        delivery.seller,
        delivery.buyer,
        delivery.initiation_time,
        delivery.confirmation_time,
        delivery.metadata
    )

@external
@view
def verify_delivery_for_parties(tracking_id: uint256, expected_seller: address, expected_buyer: address) -> bool:
    """Verify delivery is confirmed for specific seller/buyer pair"""
    delivery: Delivery = self.deliveries[tracking_id]
    return (
        delivery.initiated and
        delivery.confirmed and
        not delivery.disputed and
        delivery.seller == expected_seller and
        delivery.buyer == expected_buyer
    )
