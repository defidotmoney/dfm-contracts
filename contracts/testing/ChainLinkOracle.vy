# @version 0.3.10

"""
@notice Simple Chainlink passthrough oracle
@dev For testing purposes only
"""

interface ChainlinkAggregator:
    # Returns: (roundId, answer, startedAt, updatedAt, answeredInRound)
    # answer
    # is the answer for the given round
    # answeredInRound
    # is the round ID of the round in which the answer was computed. (Only some AggregatorV3Interface implementations return meaningful values)
    # roundId
    # is the round ID from the aggregator for which the data was retrieved combined with a phase to ensure that round IDs get larger as time moves forward.
    # startedAt
    # is the timestamp when the round was started. (Only some AggregatorV3Interface implementations return meaningful values)
    # updatedAt
    # is the timestamp when the round last was updated (i.e. answer was last computed)
    def latestRoundData() -> (uint80, int256, uint256, uint256, uint80): view
    def decimals() -> uint256: view


AGG: public(immutable(ChainlinkAggregator))
PRECISION_MUL: public(immutable(uint256))


@external
def __init__(agg: ChainlinkAggregator):
    AGG = agg
    PRECISION_MUL = 10 ** (18 - agg.decimals())


@view
@internal
def _price() -> uint256:
    price: uint256 = convert(AGG.latestRoundData()[1], uint256)
    return price * PRECISION_MUL

@external
def price_w() -> uint256:
    # State-changing price oracle in case we want to include EMA
    return self._price()


@view
@external
def price() -> uint256:
    return self._price()
