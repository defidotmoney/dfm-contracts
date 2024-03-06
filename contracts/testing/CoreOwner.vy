#pragma version 0.3.10

feeReceiver: public(address)

owner: public(address)


@external
def __init__():
    self.owner = msg.sender


@external
def transferOwnership(owner: address):
    assert msg.sender == self.owner
    self.owner = owner


@external
def setFeeReceiver(receiver: address):
    assert msg.sender == self.owner
    self.feeReceiver = receiver
