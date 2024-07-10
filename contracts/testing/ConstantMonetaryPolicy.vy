#pragma version 0.3.10
"""
Although this monetary policy works, it's only intended to be used in tests
"""

_rate: uint256


@view
@external
def rate(market: address) -> uint256:
    return self._rate


@view
@external
def rate_after_debt_change(market: address, debt_change: int256) -> uint256:
    return self._rate


@external
def rate_write(market: address) -> uint256:
    return self._rate


@external
def set_rate(rate: uint256):
    self._rate = rate
