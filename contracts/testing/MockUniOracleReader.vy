# @version 0.3.10
"""
@title Mock version of Uniswap V3 Oracle Reader
@notice https://github.com/Balmy-protocol/uniswap-v3-oracle
"""


# base token -> quote token -> price
stored_prices: public(HashMap[address, HashMap[address, uint256]])


@view
@external
def quoteAllAvailablePoolsWithTimePeriod(
    amount: uint128,
    base_token: address,
    quote_token: address,
    period: uint32
) -> uint256:
    price: uint256 = self.stored_prices[base_token][quote_token]
    assert price != 0, "UniV3 Mock: Price unset"
    return price


@external
def set_price(base_token: address, quote_token: address, price: uint256):
    self.stored_prices[base_token][quote_token] = price