# @version 0.3.10
"""
Mock version of DFMProtocolCore for titanoboa tests
"""


owner: public(address)
feeReceiver: public(address)
bridgeRelay: public(address)
guardian: public(address)


@external
def __init__(owner: address, fee_receiver: address):
    self.owner = owner
    self.feeReceiver = fee_receiver