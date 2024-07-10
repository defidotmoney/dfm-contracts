#pragma version 0.3.10
"""
@title AggMonetaryPolicy
@author Curve.Fi (with edits by defidotmoney)
@license Copyright (c) Curve.Fi, 2020-2024 - all rights reserved
@notice Monetary policy based on aggregated prices for the protocol stablecoin
@dev To simulate how the interest rate is affected by the different parameters
     within this contract: https://crvusd-rate.0xreviews.xyz/
"""

interface PriceOracle:
    def price() -> uint256: view
    def price_w() -> uint256: nonpayable

interface Controller:
    def total_debt() -> uint256: view
    def get_peg_keeper_active_debt() -> uint256: view

interface MarketOperator:
    def total_debt() -> uint256: view
    def debt_ceiling() -> uint256: view

interface CoreOwner:
    def owner() -> address: view


event SetRate:
    rate: uint256

event SetSigma:
    sigma: uint256

event SetTargetDebtFraction:
    target_debt_fraction: uint256


MAX_TARGET_DEBT_FRACTION: constant(uint256) = 10**18
MAX_SIGMA: constant(uint256) = 10**18
MIN_SIGMA: constant(uint256) = 10**14
MAX_EXP: constant(uint256) = 1000 * 10**18
MAX_RATE: constant(uint256) = 43959106799  # 300% APY
TARGET_REMAINDER: constant(uint256) = 10**17  # rate is scaled by factor of 1.9 at 90% utilization

CORE_OWNER: public(immutable(CoreOwner))
CONTROLLER: public(immutable(Controller))
STABLECOIN_ORACLE: public(immutable(PriceOracle))

rate0: public(uint256)
sigma: public(int256)  # 2 * 10**16 for example
target_debt_fraction: public(uint256)


@external
def __init__(
    core: CoreOwner,
    controller: Controller,
    stable_oracle: PriceOracle,
    rate0: uint256,
    sigma: uint256,
    target_debt_fraction: uint256
):
    """
    @notice Contract constructor
    @param core `DFMProtocolCore` address. Ownership is inherited from this contract.
    @param controller `MainController` address.
    @param stable_oracle `AggregateStablePrice` address. Used to determine the stablecoin price.
    @param rate0 Base per-second interest rate charged.
    @param sigma Initial sigma value.
    @param target_debt_fraction Ideal peg keeper debt fraction.
    """
    CORE_OWNER = core
    CONTROLLER = controller
    STABLECOIN_ORACLE = stable_oracle

    assert sigma >= MIN_SIGMA
    assert sigma <= MAX_SIGMA
    assert target_debt_fraction > 0
    assert target_debt_fraction <= MAX_TARGET_DEBT_FRACTION
    assert rate0 <= MAX_RATE
    self.rate0 = rate0
    self.sigma = convert(sigma, int256)
    self.target_debt_fraction = target_debt_fraction


@view
@external
def owner() -> address:
    return CORE_OWNER.owner()


@view
@external
def rate(market: address) -> uint256:
    """
    @notice Returns the new interest rate for the given market, with 1e18 precision
    @dev Read-only version used in view methods. Returns the same value as `rate_write`.
         Note that the rate returned here may not be the same as the actual rate currently
         charged by the market. This rate is applied during a state-changing interaction
         with the market. To get the current rate you must call `AMM.rate()`.
    @param market Address of the market to calculate the rate for
    @return New per-second interest rate
    """
    return self.calculate_rate(market, STABLECOIN_ORACLE.price(), 0)


@view
@external
def rate_after_debt_change(market: address, debt_change: int256) -> uint256:
    """
    @notice Calculates the expected interest rate for the given market, based on a
            change to the market's total debt.
    @param market Address of the market to calculate the rate for
    @param debt_change Debt adjustment amount. A positive value mints, negative burns.
    @return New per-second interest rate
    """
    return self.calculate_rate(market, STABLECOIN_ORACLE.price(), debt_change)


@external
def rate_write(market: address) -> uint256:
    """
    @notice Returns the new interest rate for the given market, with 1e18 precision
    @dev It is preferred to call this method over `rate` during on-chain interaction.
         Note that the rate returned here may not be the same as the actual rate currently
         charged by the market. This rate is applied during a state-changing interaction
         with the market. To get the current rate you must call `AMM.rate()`.
    @param market Address of the market to calculate the rate for
    @return New per-second interest rate
    """
    return self.calculate_rate(market, STABLECOIN_ORACLE.price_w(), 0)


@external
def set_rate(rate: uint256):
    """
    @notice Set the rate0 variable
    @dev rate0 determines the base per-second interest rate charged.
         To calculate from APY: `rate0 = 10**18 * ((apy + 1) ** (1 / 31536000) - 1)`
    """
    self._assert_only_owner()
    assert rate <= MAX_RATE
    self.rate0 = rate
    log SetRate(rate)


@external
def set_sigma(sigma: uint256):
    """
    @notice Set the sigma variable
    @dev Sigma determines how quickly rates increase and decrease due to a stablecoin
         depeg. A lower value corresponds to a quicker interest rate adjustment.
    """
    self._assert_only_owner()
    assert sigma >= MIN_SIGMA
    assert sigma <= MAX_SIGMA

    self.sigma = convert(sigma, int256)
    log SetSigma(sigma)


@external
def set_target_debt_fraction(target_debt_fraction: uint256):
    """
    @notice Set the target peg keeper debt fraction
    @dev The actual debt fraction is calculated as `peg_keeper_debt / total_debt`.
         As the debt fraction increases the rate goes lower. As the debt fraction
         decreases the rate goes higher.
    @param target_debt_fraction Ideal peg keeper debt fraction, expressed
                                as a whole number out of 1e18.
    """
    self._assert_only_owner()
    assert target_debt_fraction <= MAX_TARGET_DEBT_FRACTION

    self.target_debt_fraction = target_debt_fraction
    log SetTargetDebtFraction(target_debt_fraction)


@view
@internal
def _assert_only_owner():
    assert msg.sender == CORE_OWNER.owner(), "DFM:MP Only owner"


@pure
@internal
def exp(power: int256) -> uint256:
    if power <= -41446531673892821376:
        return 0

    if power >= 135305999368893231589:
        # Return MAX_EXP when we are in overflow mode
        return MAX_EXP

    x: int256 = unsafe_div(unsafe_mul(power, 2**96), 10**18)

    k: int256 = unsafe_div(
        unsafe_add(
            unsafe_div(unsafe_mul(x, 2**96), 54916777467707473351141471128),
            2**95),
        2**96)
    x = unsafe_sub(x, unsafe_mul(k, 54916777467707473351141471128))

    y: int256 = unsafe_add(x, 1346386616545796478920950773328)
    y = unsafe_add(unsafe_div(unsafe_mul(y, x), 2**96), 57155421227552351082224309758442)
    p: int256 = unsafe_sub(unsafe_add(y, x), 94201549194550492254356042504812)
    p = unsafe_add(unsafe_div(unsafe_mul(p, y), 2**96), 28719021644029726153956944680412240)
    p = unsafe_add(unsafe_mul(p, x), (4385272521454847904659076985693276 * 2**96))

    q: int256 = x - 2855989394907223263936484059900
    q = unsafe_add(unsafe_div(unsafe_mul(q, x), 2**96), 50020603652535783019961831881945)
    q = unsafe_sub(unsafe_div(unsafe_mul(q, x), 2**96), 533845033583426703283633433725380)
    q = unsafe_add(unsafe_div(unsafe_mul(q, x), 2**96), 3604857256930695427073651918091429)
    q = unsafe_sub(unsafe_div(unsafe_mul(q, x), 2**96), 14423608567350463180887372962807573)
    q = unsafe_add(unsafe_div(unsafe_mul(q, x), 2**96), 26449188498355588339934803723976023)

    return shift(
        unsafe_mul(convert(unsafe_div(p, q), uint256), 3822833074963236453042738258902158003155416615667),
        unsafe_sub(k, 195))


@view
@internal
def calculate_rate(market: address, _price: uint256, debt_change: int256) -> uint256:
    sigma: int256 = self.sigma
    target_debt_fraction: uint256 = self.target_debt_fraction

    p: int256 = convert(_price, int256)
    pk_debt: uint256 = CONTROLLER.get_peg_keeper_active_debt()

    # apply `debt_change` to market total debt, with a lower bound of zero
    market_debt: uint256 = 0
    if market != empty(address):
        market_debt = MarketOperator(market).total_debt()
        if debt_change < 0 and market_debt < convert(-debt_change, uint256):
            # also bound `debt_change` to the market debt, so that total debt adjustment is accurate
            debt_change = -convert(market_debt, int256)
            market_debt = 0
        else:
            market_debt = convert(convert(market_debt, int256) + debt_change, uint256)

    power: int256 = (10**18 - p) * 10**18 / sigma  # high price -> negative pow -> low rate
    if pk_debt > 0:
        total_debt: uint256 = CONTROLLER.total_debt()
        if total_debt == 0:
            return 0

        if debt_change != 0:
            # apply `debt_change` to total debt, with a lower bound of zero
            total_debt = convert(max(convert(total_debt, int256) + debt_change, 0), uint256)

        power -= convert(pk_debt * 10**18 / total_debt * 10**18 / target_debt_fraction, int256)

    # Rate accounting for stablecoin price and PegKeeper debt
    rate: uint256 = self.rate0 * min(self.exp(power), MAX_EXP) / 10**18

    # Account for individual debt ceiling to dynamically tune rate depending on filling the market
    if market != empty(address):
        ceiling: uint256 = MarketOperator(market).debt_ceiling()
        if ceiling > 0:
            f: uint256 = min(market_debt * 10**18 / ceiling, 10**18 - TARGET_REMAINDER / 1000)
            rate = min(rate * ((10**18 - TARGET_REMAINDER) + TARGET_REMAINDER * 10**18 / (10**18 - f)) / 10**18, MAX_RATE)

    return rate
