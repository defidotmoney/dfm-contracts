# @version ^0.3.9
"""
@notice Chainlink Aggregator Mock for testing
"""

decimals: public(uint8)
price: int256
updated_at: uint256


@payable
@external
def __init__(decimals: uint8, price: int256):
    self.decimals = decimals
    self.price = price


@external
@view
def latestRoundData() -> (uint80, int256, uint256, uint256, uint80):
    """
    returns (roundId, answer, startedAt, updatedAt, answeredInRound)
    """
    round_id: uint80 = convert(block.number, uint80)

    updated_at: uint256 = self.updated_at
    if updated_at == 0:
        # if unset we assume tests either do not require or prefer it to be up-to-date
        updated_at = block.timestamp

    return round_id, self.price * 10**convert(self.decimals, int256), updated_at, updated_at, round_id


@external
def set_price(price: int256):
    self.price = price


@external
def set_updated_at(updated_at: uint256):
    self.updated_at = updated_at