#pragma version 0.3.10

feeReceiver: public(address)

owner: public(address)


@external
def __init__(fee_receiver: address):
    self.owner = msg.sender
    self.feeReceiver = fee_receiver


@external
def transferOwnership(owner: address):
    assert msg.sender == self.owner
    self.owner = owner


@external
def setFeeReceiver(receiver: address):
    assert msg.sender == self.owner
    self.feeReceiver = receiver
