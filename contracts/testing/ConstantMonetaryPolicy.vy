# @version 0.3.10
"""
Although this monetary policy works, it's only intended to be used in tests
"""

rate: public(uint256)


@external
def rate_write(controller: address) -> uint256:
    return self.rate


@external
def set_rate(rate: uint256):
    self.rate = rate
