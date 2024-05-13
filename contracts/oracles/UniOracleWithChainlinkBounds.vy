# @version 0.3.10
"""
@title UniOracleWithChainlinkBounds
@dev Returns UniswapV3 TWAP, bounded by Chainlink
@license MIT
"""


interface ERC20:
    def decimals() -> uint256: view

interface UniOracleReader:
    def quoteAllAvailablePoolsWithTimePeriod(
        amount: uint128,
        base_token: ERC20,
        quote_token: ERC20,
        period: uint32
    ) -> uint256: view
    def prepareAllAvailablePoolsWithTimePeriod(
        base_token: ERC20,
        quote_token: ERC20,
        period: uint32
    ): nonpayable

interface ChainlinkAggregator:
    def latestRoundData() -> (uint256, int256): view  # (roundId, answer)
    def decimals() -> uint256: view

interface CoreOwner:
    def owner() -> address: view


MAX_DEVIATION_PREC: public(constant(uint256)) = 10000
BASE_PRECISION: immutable(uint128)
QUOTE_PRECISION_MUL: immutable(uint256)
CHAINLINK_PRECISION_MUL: immutable(uint256)

CORE_OWNER: public(immutable(CoreOwner))
BASE_TOKEN: public(immutable(ERC20))
QUOTE_TOKEN: public(immutable(ERC20))
UNI_ORACLE_READER: public(immutable(UniOracleReader))
CHAINLINK_AGG: public(immutable(ChainlinkAggregator))

twap_period: public(uint32)
max_deviation: public(uint256)


@external
def __init__(
    core: CoreOwner,
    base_token: ERC20,
    quote_token: ERC20,
    chainlink: ChainlinkAggregator,
    twap_period: uint32,
    max_deviation: uint256
):
    # Vyper does not like Contract types as public constants
    UNI_ORACLE_READER = UniOracleReader(0xB210CE856631EeEB767eFa666EC7C1C57738d438)

    CORE_OWNER = core
    BASE_TOKEN = base_token
    QUOTE_TOKEN = quote_token
    CHAINLINK_AGG = chainlink

    BASE_PRECISION = convert(10 ** base_token.decimals(), uint128)
    QUOTE_PRECISION_MUL = 10 ** (18 - quote_token.decimals())
    CHAINLINK_PRECISION_MUL = 10 ** (18 - chainlink.decimals())

    self.max_deviation = max_deviation
    self._set_period(twap_period)


@view
@external
def owner() -> address:
    return CORE_OWNER.owner()


@view
@external
def get_uniswap_twap(period: uint32 = 0) -> uint256:
    p: uint32 = period
    if period == 0:
        p = self.twap_period
    return self._get_uniswap_twap(p)


@view
@external
def get_chainlink_answer() -> uint256:
    return self._get_chainlink_answer()


@external
@view
def price() -> uint256:
    return self._price()


@external
def price_w() -> uint256:
    return self._price()


@external
def set_twap_period(period: uint32):
    """
    @notice Set the number of seconds from which to calculate the TWAP
    """
    self._assert_only_owner()
    self._set_period(period)


@external
def set_max_deviation(max_deviation: uint256):
    """
    @notice Set the max allowable deviation between the TWAP and Chainlink's latest answer
    @dev If the TWAP falls outside the allowable range, the nearest allowed value is returned
    """
    self._assert_only_owner()
    assert max_deviation <= MAX_DEVIATION_PREC

    self.max_deviation = max_deviation


@view
@internal
def _assert_only_owner():
    assert msg.sender == CORE_OWNER.owner(), "DFM:O Only owner"


@view
@internal
def _get_uniswap_twap(period: uint32) -> uint256:
    twap: uint256 = UNI_ORACLE_READER.quoteAllAvailablePoolsWithTimePeriod(
        BASE_PRECISION,
        BASE_TOKEN,
        QUOTE_TOKEN,
        period
    )
    return twap * QUOTE_PRECISION_MUL


@view
@internal
def _get_chainlink_answer() -> uint256:
    answer: int256 = CHAINLINK_AGG.latestRoundData()[1]
    return convert(answer, uint256) * CHAINLINK_PRECISION_MUL


@view
@internal
def _price() -> uint256:
    twap: uint256 = self._get_uniswap_twap(self.twap_period)
    cl: uint256 = self._get_chainlink_answer()

    if twap > cl:
        cl_upper: uint256 = cl * (MAX_DEVIATION_PREC + self.max_deviation) / MAX_DEVIATION_PREC
        if cl_upper < twap:
            return cl_upper
    else:
        cl_lower: uint256 = cl * (MAX_DEVIATION_PREC - self.max_deviation) / MAX_DEVIATION_PREC
        if cl_lower > twap:
            return cl_lower

    return twap


@internal
def _set_period(period: uint32):
    UNI_ORACLE_READER.prepareAllAvailablePoolsWithTimePeriod(BASE_TOKEN, QUOTE_TOKEN, period)
    self.twap_period = period
