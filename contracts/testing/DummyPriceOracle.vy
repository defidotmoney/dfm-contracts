# @version 0.3.10

"""
This contract is for testing only.
If you see it on mainnet - it won't be used for anything except testing the actual deployment
"""

event PriceWrite:
    pass


price: public(uint256)
_price_w: uint256

@external
def __init__(price: uint256):
    self.price = price


@external
def price_w() -> uint256:
    # State-changing price oracle in case we want to include EMA
    log PriceWrite()
    price: uint256 = self._price_w
    if price == 0:
        price = self.price
    return price


@external
def set_price(price: uint256):
    self.price = price


@external
def set_price_w(price_w: uint256):
    """
    @dev Set a distinct response for `price_w()`. If unset, returns the same value as `price()`.
    """
    self._price_w = price_w
