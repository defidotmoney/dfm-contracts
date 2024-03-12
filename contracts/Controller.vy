# @version 0.3.10
"""
@title crvUSD Controller
@author Curve.Fi
@license Copyright (c) Curve.Fi, 2020-2023 - all rights reserved
"""

interface LLAMMA:
    def A() -> uint256: view
    def get_p() -> uint256: view
    def get_base_price() -> uint256: view
    def active_band() -> int256: view
    def active_band_with_skip() -> int256: view
    def p_oracle_up(n: int256) -> uint256: view
    def p_oracle_down(n: int256) -> uint256: view
    def deposit_range(account: address, amount: uint256, n1: int256, n2: int256): nonpayable
    def read_user_tick_numbers(receiver: address) -> int256[2]: view
    def get_sum_xy(account: address) -> uint256[2]: view
    def withdraw(account: address, frac: uint256) -> uint256[2]: nonpayable
    def get_x_down(account: address) -> uint256: view
    def get_rate_mul() -> uint256: view
    def set_fee(fee: uint256): nonpayable
    def set_admin_fee(fee: uint256): nonpayable
    def price_oracle() -> uint256: view
    def can_skip_bands(n_end: int256) -> bool: view
    def set_price_oracle(price_oracle: PriceOracle): nonpayable
    def admin_fees_x() -> uint256: view
    def admin_fees_y() -> uint256: view
    def reset_admin_fees() -> uint256[2]: nonpayable
    def has_liquidity(account: address) -> bool: view
    def bands_x(n: int256) -> uint256: view
    def bands_y(n: int256) -> uint256: view
    def set_liquidity_mining_hook(account: address): nonpayable

interface ERC20:
    def mint(_to: address, _value: uint256) -> bool: nonpayable
    def burn(_to: address, _value: uint256) -> bool: nonpayable
    def transferFrom(_from: address, _to: address, _value: uint256) -> bool: nonpayable
    def transfer(_to: address, _value: uint256) -> bool: nonpayable
    def decimals() -> uint256: view
    def approve(_spender: address, _value: uint256) -> bool: nonpayable
    def balanceOf(_from: address) -> uint256: view

interface MonetaryPolicy:
    def rate_write() -> uint256: nonpayable

interface Factory:
    def WETH() -> address: view

interface ICoreOwner:
    def owner() -> address: view
    def stableCoin() -> ERC20: view

interface PriceOracle:
    def price() -> uint256: view
    def price_w() -> uint256: nonpayable


event UserState:
    account: indexed(address)
    collateral: uint256
    debt: uint256
    n1: int256
    n2: int256
    liquidation_discount: uint256

event SetMonetaryPolicy:
    monetary_policy: address

event SetBorrowingDiscounts:
    loan_discount: uint256
    liquidation_discount: uint256


struct Loan:
    initial_debt: uint256
    rate_mul: uint256

struct Position:
    account: address
    x: uint256
    y: uint256
    debt: uint256
    health: int256

struct CallbackData:
    active_band: int256
    stablecoins: uint256
    collateral: uint256


FACTORY: public(immutable(address))
CORE_OWNER: public(immutable(ICoreOwner))
STABLECOIN: public(immutable(ERC20))
MAX_LOAN_DISCOUNT: constant(uint256) = 5 * 10**17
MIN_LIQUIDATION_DISCOUNT: constant(uint256) = 10**16 # Start liquidating when threshold reached
MAX_TICKS: constant(int256) = 50
MAX_TICKS_UINT: constant(uint256) = 50
MIN_TICKS: constant(int256) = 4
MAX_SKIP_TICKS: constant(uint256) = 1024
MAX_P_BASE_BANDS: constant(int256) = 5

MAX_RATE: constant(uint256) = 43959106799  # 300% APY

loan: HashMap[address, Loan]
liquidation_discounts: public(HashMap[address, uint256])
_total_debt: Loan

loans: public(address[2**64 - 1])  # Enumerate existing loans
loan_ix: public(HashMap[address, uint256])  # Position of the loan in the list
n_loans: public(uint256)  # Number of nonzero loans

debt_ceiling: public(uint256)
liquidation_discount: public(uint256)
loan_discount: public(uint256)

COLLATERAL_TOKEN: immutable(ERC20)
COLLATERAL_PRECISION: immutable(uint256)

AMM: public(immutable(LLAMMA))
A: immutable(uint256)
Aminus1: immutable(uint256)
LOG2_A_RATIO: immutable(int256)  # log(A / (A - 1))
SQRT_BAND_RATIO: immutable(uint256)

MAX_ADMIN_FEE: constant(uint256) = 10**18  # 100%
MIN_FEE: constant(uint256) = 10**6  # 1e-12, still needs to be above 0
MAX_FEE: immutable(uint256)  # MIN_TICKS / A: for example, 4% max fee for A=100

DEAD_SHARES: constant(uint256) = 1000


@external
def __init__(
        core: ICoreOwner,
        collateral_token: address,
        amm_implementation: address,
        debt_ceiling: uint256,
        loan_discount: uint256,
        liquidation_discount: uint256,
        _A: uint256,
        _base_price: uint256,
        fee: uint256,
        admin_fee: uint256,
        _price_oracle_contract: address
        ):
    """
    @notice Controller constructor deployed by the factory from blueprint
    @param collateral_token Token to use for collateral
    @param loan_discount Discount of the maximum loan size compare to get_x_down() value
    @param liquidation_discount Discount of the maximum loan size compare to
           get_x_down() for "bad liquidation" purposes
    @param amm_implementation AMM address (Already deployed from blueprint)
    """

    FACTORY = msg.sender
    CORE_OWNER = core
    STABLECOIN = core.stableCoin()

    self.debt_ceiling = debt_ceiling
    self.liquidation_discount = liquidation_discount
    self.loan_discount = loan_discount
    self._total_debt.rate_mul = 10**18

    A = _A
    Aminus1 = unsafe_sub(_A, 1)
    LOG2_A_RATIO = self.log2(unsafe_div(_A * 10**18, unsafe_sub(_A, 1)))
    MAX_FEE = min(unsafe_div(10**18 * MIN_TICKS, A), 10**17)

    COLLATERAL_TOKEN = ERC20(collateral_token)
    COLLATERAL_PRECISION = pow_mod256(10, 18 - ERC20(collateral_token).decimals())

    SQRT_BAND_RATIO = isqrt(unsafe_div(10**36 * _A, unsafe_sub(_A, 1)))

    A_ratio: uint256 = 10**18 * A / (A - 1)
    amm: address = create_from_blueprint(
        amm_implementation,
        STABLECOIN.address, 10**(18 - STABLECOIN.decimals()),
        collateral_token, COLLATERAL_PRECISION,  # <- This validates ERC20 ABI
        A, SQRT_BAND_RATIO, self.ln_int(A_ratio),
        _base_price, fee, admin_fee, _price_oracle_contract, msg.sender,
        code_offset=3)
    AMM = LLAMMA(amm)


@internal
@pure
def log2(_x: uint256) -> int256:
    """
    @notice int(1e18 * log2(_x / 1e18))
    """
    # adapted from: https://medium.com/coinmonks/9aef8515136e
    # and vyper log implementation
    # Might use more optimal solmate's log
    inverse: bool = _x < 10**18
    res: uint256 = 0
    x: uint256 = _x
    if inverse:
        x = 10**36 / x
    t: uint256 = 2**7
    for i in range(8):
        p: uint256 = pow_mod256(2, t)
        if x >= unsafe_mul(p, 10**18):
            x = unsafe_div(x, p)
            res = unsafe_add(unsafe_mul(t, 10**18), res)
        t = unsafe_div(t, 2)
    d: uint256 = 10**18
    for i in range(34):  # 10 decimals: math.log(10**10, 2) == 33.2. Need more?
        if (x >= 2 * 10**18):
            res = unsafe_add(res, d)
            x = unsafe_div(x, 2)
        x = unsafe_div(unsafe_mul(x, x), 10**18)
        d = unsafe_div(d, 2)
    if inverse:
        return -convert(res, int256)
    else:
        return convert(res, int256)


@internal
@pure
def ln_int(_x: uint256) -> int256:
    """
    @notice Logarithm ln() function based on log2. Not very gas-efficient but brief
    """
    # adapted from: https://medium.com/coinmonks/9aef8515136e
    # and vyper log implementation
    # This can be much more optimal but that's not important here
    x: uint256 = _x
    res: uint256 = 0
    for i in range(8):
        t: uint256 = 2**(7 - i)
        p: uint256 = 2**t
        if x >= p * 10**18:
            x /= p
            res += t * 10**18
    d: uint256 = 10**18
    for i in range(59):  # 18 decimals: math.log2(10**10) == 59.7
        if (x >= 2 * 10**18):
            res += d
            x /= 2
        x = x * x / 10**18
        d /= 2
    # Now res = log2(x)
    # ln(x) = log2(x) / log2(e)
    return convert(res * 10**18 / 1442695040888963328, int256)
## End of low-level math


@external
@view
def amm() -> LLAMMA:
    """
    @notice Address of the AMM
    """
    return AMM


@external
@view
def collateral_token() -> ERC20:
    """
    @notice Address of the collateral token
    """
    return COLLATERAL_TOKEN


@internal
@view
def _debt(account: address) -> (uint256, uint256):
    """
    @notice Get the value of debt without changing the state
    @param account User address
    @return Value of debt
    """
    rate_mul: uint256 = AMM.get_rate_mul()
    loan: Loan = self.loan[account]
    if loan.initial_debt == 0:
        return (0, rate_mul)
    else:
        return (loan.initial_debt * rate_mul / loan.rate_mul, rate_mul)


@external
@view
@nonreentrant('lock')
def debt(account: address) -> uint256:
    """
    @notice Get the value of debt without changing the state
    @param account User address
    @return Value of debt
    """
    return self._debt(account)[0]


@external
@view
@nonreentrant('lock')
def loan_exists(account: address) -> bool:
    """
    @notice Check whether there is a loan of `account` in existence
    """
    return self.loan[account].initial_debt > 0


# No decorator because used in monetary policy
@external
@view
def total_debt() -> uint256:
    """
    @notice Total debt of this controller
    """
    rate_mul: uint256 = AMM.get_rate_mul()
    loan: Loan = self._total_debt
    return loan.initial_debt * rate_mul / loan.rate_mul


@internal
@view
def get_y_effective(collateral: uint256, N: uint256, discount: uint256) -> uint256:
    """
    @notice Intermediary method which calculates y_effective defined as x_effective / p_base,
            however discounted by loan_discount.
            x_effective is an amount which can be obtained from collateral when liquidating
    @param collateral Amount of collateral to get the value for
    @param N Number of bands the deposit is made into
    @param discount Loan discount at 1e18 base (e.g. 1e18 == 100%)
    @return y_effective
    """
    # x_effective = sum_{i=0..N-1}(y / N * p(n_{n1+i})) =
    # = y / N * p_oracle_up(n1) * sqrt((A - 1) / A) * sum_{0..N-1}(((A-1) / A)**k)
    # === d_y_effective * p_oracle_up(n1) * sum(...) === y_effective * p_oracle_up(n1)
    # d_y_effective = y / N / sqrt(A / (A - 1))
    # d_y_effective: uint256 = collateral * unsafe_sub(10**18, discount) / (SQRT_BAND_RATIO * N)
    # Make some extra discount to always deposit lower when we have DEAD_SHARES rounding
    d_y_effective: uint256 = collateral * unsafe_sub(
        10**18, min(discount + unsafe_div((DEAD_SHARES * 10**18), max(unsafe_div(collateral, N), DEAD_SHARES)), 10**18)
    ) / unsafe_mul(SQRT_BAND_RATIO, N)
    y_effective: uint256 = d_y_effective
    for i in range(1, MAX_TICKS_UINT):
        if i == N:
            break
        d_y_effective = unsafe_div(d_y_effective * Aminus1, A)
        y_effective = unsafe_add(y_effective, d_y_effective)
    return y_effective


@internal
@view
def _calculate_debt_n1(collateral: uint256, debt: uint256, N: uint256) -> int256:
    """
    @notice Calculate the upper band number for the deposit to sit in to support
            the given debt. Reverts if requested debt is too high.
    @param collateral Amount of collateral (at its native precision)
    @param debt Amount of requested debt
    @param N Number of bands to deposit into
    @return Upper band n1 (n1 <= n2) to deposit into. Signed integer
    """
    assert debt > 0, "No loan"
    n0: int256 = AMM.active_band()
    p_base: uint256 = AMM.p_oracle_up(n0)

    # x_effective = y / N * p_oracle_up(n1) * sqrt((A - 1) / A) * sum_{0..N-1}(((A-1) / A)**k)
    # === d_y_effective * p_oracle_up(n1) * sum(...) === y_effective * p_oracle_up(n1)
    # d_y_effective = y / N / sqrt(A / (A - 1))
    y_effective: uint256 = self.get_y_effective(collateral * COLLATERAL_PRECISION, N, self.loan_discount)
    # p_oracle_up(n1) = base_price * ((A - 1) / A)**n1

    # We borrow up until min band touches p_oracle,
    # or it touches non-empty bands which cannot be skipped.
    # We calculate required n1 for given (collateral, debt),
    # and if n1 corresponds to price_oracle being too high, or unreachable band
    # - we revert.

    # n1 is band number based on adiabatic trading, e.g. when p_oracle ~ p
    y_effective = unsafe_div(y_effective * p_base, debt + 1)  # Now it's a ratio

    # n1 = floor(log2(y_effective) / self.logAratio)
    # EVM semantics is not doing floor unlike Python, so we do this
    assert y_effective > 0, "Amount too low"
    n1: int256 = self.log2(y_effective)  # <- switch to faster ln() XXX?
    if n1 < 0:
        n1 -= unsafe_sub(LOG2_A_RATIO, 1)  # This is to deal with vyper's rounding of negative numbers
    n1 = unsafe_div(n1, LOG2_A_RATIO)

    n1 = min(n1, 1024 - convert(N, int256)) + n0
    if n1 <= n0:
        assert AMM.can_skip_bands(n1 - 1), "Debt too high"

    # Let's not rely on active_band corresponding to price_oracle:
    # this will be not correct if we are in the area of empty bands
    assert AMM.p_oracle_up(n1) < AMM.price_oracle(), "Debt too high"

    return n1


@internal
@view
def max_p_base() -> uint256:
    """
    @notice Calculate max base price including skipping bands
    """
    p_oracle: uint256 = AMM.price_oracle()
    # Should be correct unless price changes suddenly by MAX_P_BASE_BANDS+ bands
    n1: int256 = self.log2(AMM.get_base_price() * 10**18 / p_oracle)
    if n1 < 0:
        n1 -= LOG2_A_RATIO - 1  # This is to deal with vyper's rounding of negative numbers
    n1 = unsafe_div(n1, LOG2_A_RATIO) + MAX_P_BASE_BANDS
    n_min: int256 = AMM.active_band_with_skip()
    n1 = max(n1, n_min + 1)
    p_base: uint256 = AMM.p_oracle_up(n1)

    for i in range(MAX_SKIP_TICKS + 1):
        n1 -= 1
        if n1 <= n_min:
            break
        p_base_prev: uint256 = p_base
        p_base = unsafe_div(p_base * A, Aminus1)
        if p_base > p_oracle:
            return p_base_prev

    return p_base


@external
@view
@nonreentrant('lock')
def max_borrowable(collateral: uint256, N: uint256, current_debt: uint256 = 0) -> uint256:
    """
    @notice Calculation of maximum which can be borrowed (details in comments)
    @param collateral Collateral amount against which to borrow
    @param N number of bands to have the deposit into
    @param current_debt Current debt of the account (if any)
    @return Maximum amount of stablecoin to borrow
    """
    # Calculation of maximum which can be borrowed.
    # It corresponds to a minimum between the amount corresponding to price_oracle
    # and the one given by the min reachable band.
    #
    # Given by p_oracle (perhaps needs to be multiplied by (A - 1) / A to account for mid-band effects)
    # x_max ~= y_effective * p_oracle
    #
    # Given by band number:
    # if n1 is the lowest empty band in the AMM
    # xmax ~= y_effective * amm.p_oracle_up(n1)
    #
    # When n1 -= 1:
    # p_oracle_up *= A / (A - 1)

    # TODO refactor this function based on mint/burn changes
    y_effective: uint256 = self.get_y_effective(collateral * COLLATERAL_PRECISION, N, self.loan_discount)

    x: uint256 = unsafe_sub(max(unsafe_div(y_effective * self.max_p_base(), 10**18), 1), 1)
    x = unsafe_div(x * (10**18 - 10**14), 10**18)  # Make it a bit smaller
    return min(x, STABLECOIN.balanceOf(self) + current_debt)  # Cannot borrow beyond the amount of coins Controller has


@external
@view
@nonreentrant('lock')
def min_collateral(debt: uint256, N: uint256) -> uint256:
    """
    @notice Minimal amount of collateral required to support debt
    @param debt The debt to support
    @param N Number of bands to deposit into
    @return Minimal collateral required
    """
     # Add N**2 to account for precision loss in multiple bands, e.g. N / (y/N) = N**2 / y
    return unsafe_div(unsafe_div(debt * 10**18 / self.max_p_base() * 10**18 / self.get_y_effective(10**18, N, self.loan_discount) + N * (N + 2 * DEAD_SHARES), COLLATERAL_PRECISION) * 10**18, 10**18 - 10**14)


@external
@view
@nonreentrant('lock')
def calculate_debt_n1(collateral: uint256, debt: uint256, N: uint256) -> int256:
    """
    @notice Calculate the upper band number for the deposit to sit in to support
            the given debt. Reverts if requested debt is too high.
    @param collateral Amount of collateral (at its native precision)
    @param debt Amount of requested debt
    @param N Number of bands to deposit into
    @return Upper band n1 (n1 <= n2) to deposit into. Signed integer
    """
    return self._calculate_debt_n1(collateral, debt, N)


@pure
@internal
def _uint_plus_int(initial: uint256, adjustment: int256) -> uint256:
    if adjustment < 0:
        return initial - convert(-adjustment, uint256)
    else:
        return initial + convert(adjustment, uint256)


@internal
def _increase_total_debt(amount: uint256, rate_mul: uint256) -> uint256:
    stored_debt: uint256 = self._total_debt.initial_debt
    total_debt: uint256 = stored_debt * rate_mul / self._total_debt.rate_mul
    if amount > 0:
        total_debt += amount
        assert total_debt <= self.debt_ceiling, "Exceeds debt ceiling"

    self._total_debt = Loan({initial_debt: total_debt, rate_mul: rate_mul})
    return total_debt - stored_debt


@internal
def _decrease_total_debt(amount: uint256, rate_mul: uint256) -> int256:
    stored_debt: uint256 = self._total_debt.initial_debt
    total_debt: uint256 = stored_debt * rate_mul / self._total_debt.rate_mul
    if total_debt > amount:
        total_debt = unsafe_sub(total_debt, amount)
    else:
        total_debt = 0

    self._total_debt = Loan({initial_debt: total_debt, rate_mul: rate_mul})
    return convert(total_debt, int256) - convert(stored_debt, int256)


@external
@nonreentrant('lock')
def create_loan(account: address, coll_amount: uint256, debt_amount: uint256, num_bands: uint256) -> uint256:
    """
    @notice Create loan
    @param coll_amount Amount of collateral to use
    @param debt_amount Stablecoin amount to mint
    @param num_bands Number of bands to deposit into (to do autoliquidation-deliquidation),
           can be from MIN_TICKS to MAX_TICKS
    """
    assert msg.sender == FACTORY

    assert self.loan[account].initial_debt == 0, "Loan already created"
    assert num_bands > MIN_TICKS-1, "Need more ticks"
    assert num_bands < MAX_TICKS+1, "Need less ticks"

    n1: int256 = self._calculate_debt_n1(coll_amount, debt_amount, num_bands)
    n2: int256 = n1 + convert(num_bands - 1, int256)

    rate_mul: uint256 = AMM.get_rate_mul()
    self.loan[account] = Loan({initial_debt: debt_amount, rate_mul: rate_mul})
    liquidation_discount: uint256 = self.liquidation_discount
    self.liquidation_discounts[account] = liquidation_discount

    n_loans: uint256 = self.n_loans
    self.loans[n_loans] = account
    self.loan_ix[account] = n_loans
    self.n_loans = unsafe_add(n_loans, 1)

    debt_increase: uint256 = self._increase_total_debt(debt_amount, rate_mul)

    AMM.deposit_range(account, coll_amount, n1, n2)

    log UserState(account, coll_amount, debt_amount, n1, n2, liquidation_discount)

    return debt_increase


@external
@nonreentrant('lock')
def adjust_loan(account: address, coll_change: int256, debt_change: int256, max_active_band: int256) -> int256:
    assert msg.sender == FACTORY

    account_debt: uint256 = 0
    rate_mul: uint256 = 0
    account_debt, rate_mul = self._debt(account)
    assert account_debt > 0, "Loan doesn't exist"
    ns: int256[2] = AMM.read_user_tick_numbers(account)
    size: uint256 = convert(unsafe_add(unsafe_sub(ns[1], ns[0]), 1), uint256)

    active_band: int256 = AMM.active_band_with_skip()
    assert active_band <= max_active_band

    if ns[0] > active_band:
        # Not in liquidation - can move bands
        coll_amount: uint256 = AMM.withdraw(account, 10**18)[1]

        coll_amount = self._uint_plus_int(coll_amount, coll_change)
        account_debt = self._uint_plus_int(account_debt, debt_change)

        n1: int256 = self._calculate_debt_n1(coll_amount, account_debt, size)
        n2: int256 = n1 + unsafe_sub(ns[1], ns[0])
        AMM.deposit_range(account, coll_amount, n1, n2)
        liquidation_discount: uint256 = self.liquidation_discount
        self.liquidation_discounts[account] = liquidation_discount
        log UserState(account, coll_amount, account_debt, n1, n2, liquidation_discount)
    else:
        assert debt_change < 0 and coll_change == 0, "Can only repay when underwater"
        # Underwater - cannot move band but can avoid a bad liquidation
        log UserState(account, max_value(uint256), account_debt, ns[0], ns[1], self.liquidation_discounts[account])

    self.loan[account] = Loan({initial_debt: account_debt, rate_mul: rate_mul})
    if debt_change < 0:
        return self._decrease_total_debt(convert(-debt_change, uint256), rate_mul)
    else:
        return convert(self._increase_total_debt(convert(debt_change, uint256), rate_mul), int256)


@external
@nonreentrant('lock')
def close_loan(account: address) -> (int256, uint256, uint256[2]):
    """
    @notice Close an existing loan
    @param account The account to close the loan for
    """
    assert msg.sender == FACTORY

    account_debt: uint256 = 0
    rate_mul: uint256 = 0
    account_debt, rate_mul = self._debt(account)
    assert account_debt > 0, "Loan doesn't exist"

    xy: uint256[2] = AMM.withdraw(account, 10**18)

    log UserState(account, 0, 0, 0, 0, 0)
    self._remove_from_list(account)

    self.loan[account] = Loan({initial_debt: 0, rate_mul: 0})
    debt_adjustment: int256 = self._decrease_total_debt(account_debt, rate_mul)

    return debt_adjustment, account_debt, xy


@internal
def _remove_from_list(receiver: address):
    last_loan_ix: uint256 = self.n_loans - 1
    loan_ix: uint256 = self.loan_ix[receiver]
    assert self.loans[loan_ix] == receiver  # dev: should never fail but safety first
    self.loan_ix[receiver] = 0
    if loan_ix < last_loan_ix:  # Need to replace
        last_loan: address = self.loans[last_loan_ix]
        self.loans[loan_ix] = last_loan
        self.loan_ix[last_loan] = loan_ix
    self.n_loans = last_loan_ix


@internal
@view
def _health(account: address, debt: uint256, full: bool, liquidation_discount: uint256) -> int256:
    """
    @notice Returns position health normalized to 1e18 for the account.
            Liquidation starts when < 0, however devaluation of collateral doesn't cause liquidation
    @param account User address to calculate health for
    @param debt The amount of debt to calculate health for
    @param full Whether to take into account the price difference above the highest account's band
    @param liquidation_discount Liquidation discount to use (can be 0)
    @return Health: > 0 = good.
    """
    assert debt > 0, "Loan doesn't exist"
    health: int256 = 10**18 - convert(liquidation_discount, int256)
    health = unsafe_div(convert(AMM.get_x_down(account), int256) * health, convert(debt, int256)) - 10**18

    if full:
        ns0: int256 = AMM.read_user_tick_numbers(account)[0] # ns[1] > ns[0]
        if ns0 > AMM.active_band():  # We are not in liquidation mode
            p: uint256 = AMM.price_oracle()
            p_up: uint256 = AMM.p_oracle_up(ns0)
            if p > p_up:
                health += convert(unsafe_div(unsafe_sub(p, p_up) * AMM.get_sum_xy(account)[1] * COLLATERAL_PRECISION, debt), int256)

    return health


@external
@view
@nonreentrant('lock')
def health_calculator(account: address, coll_amount: int256, debt_amount: int256, full: bool, N: uint256 = 0) -> int256:
    """
    @notice Health predictor in case account changes the debt or collateral
    @param account Address of the account
    @param coll_amount Change in collateral amount (signed)
    @param debt_amount Change in debt amount (signed)
    @param full Whether it's a 'full' health or not
    @param N Number of bands in case loan doesn't yet exist
    @return Signed health value
    """
    ns: int256[2] = AMM.read_user_tick_numbers(account)
    debt: int256 = convert(self._debt(account)[0], int256)
    n: uint256 = N
    ld: int256 = 0
    if debt != 0:
        ld = convert(self.liquidation_discounts[account], int256)
        n = convert(unsafe_add(unsafe_sub(ns[1], ns[0]), 1), uint256)
    else:
        ld = convert(self.liquidation_discount, int256)
        ns[0] = max_value(int256)  # This will trigger a "re-deposit"

    n1: int256 = 0
    collateral: int256 = 0
    x_eff: int256 = 0
    debt += debt_amount
    assert debt > 0, "Non-positive debt"

    active_band: int256 = AMM.active_band_with_skip()

    if ns[0] > active_band:  # re-deposit
        collateral = convert(AMM.get_sum_xy(account)[1], int256) + coll_amount
        n1 = self._calculate_debt_n1(convert(collateral, uint256), convert(debt, uint256), n)
        collateral *= convert(COLLATERAL_PRECISION, int256)  # now has 18 decimals
    else:
        n1 = ns[0]
        x_eff = convert(AMM.get_x_down(account) * 10**18, int256)

    p0: int256 = convert(AMM.p_oracle_up(n1), int256)
    if ns[0] > active_band:
        x_eff = convert(self.get_y_effective(convert(collateral, uint256), n, 0), int256) * p0

    health: int256 = unsafe_div(x_eff, debt)
    health = health - unsafe_div(health * ld, 10**18) - 10**18

    if full:
        if n1 > active_band:  # We are not in liquidation mode
            p_diff: int256 = max(p0, convert(AMM.price_oracle(), int256)) - p0
            if p_diff > 0:
                health += unsafe_div(p_diff * collateral, debt)

    return health


@internal
@view
def _get_f_remove(frac: uint256, health_limit: uint256) -> uint256:
    # f_remove = ((1 + h / 2) / (1 + h) * (1 - frac) + frac) * frac
    f_remove: uint256 = 10 ** 18
    if frac < 10 ** 18:
        f_remove = unsafe_div(unsafe_mul(unsafe_add(10 ** 18, unsafe_div(health_limit, 2)), unsafe_sub(10 ** 18, frac)), unsafe_add(10 ** 18, health_limit))
        f_remove = unsafe_div(unsafe_mul(unsafe_add(f_remove, frac), frac), 10 ** 18)

    return f_remove


@external
@nonreentrant('lock')
def liquidate(caller: address, target: address, min_x: uint256, frac: uint256) -> (int256, uint256, uint256[2]):
    """
    @notice Perform a bad liquidation (or self-liquidation) of account if health is not good
    @param target Address of the account to be liquidated
    @param min_x Minimal amount of stablecoin to receive (to avoid liquidators being sandwiched)
    @param frac Fraction to liquidate; 100% = 10**18
    """
    health_limit: uint256 = 0
    if target != caller:
        health_limit = self.liquidation_discounts[target]

    debt: uint256 = 0
    rate_mul: uint256 = 0
    debt, rate_mul = self._debt(target)

    if health_limit != 0:
        assert self._health(target, debt, True, health_limit) < 0, "Not enough rekt"

    final_debt: uint256 = debt
    debt = unsafe_div(debt * frac, 10**18)
    assert debt > 0
    final_debt = unsafe_sub(final_debt, debt)

    # Withdraw sender's stablecoin and collateral to our contract
    # When frac is set - we withdraw a bit less for the same debt fraction
    # f_remove = ((1 + h/2) / (1 + h) * (1 - frac) + frac) * frac
    # where h is health limit.
    # This is less than full h discount but more than no discount
    xy: uint256[2] = AMM.withdraw(target, self._get_f_remove(frac, health_limit))  # [stable, collateral]

    # x increase in same block -> price up -> good
    # x decrease in same block -> price down -> bad
    assert xy[0] >= min_x, "Slippage"

    self.loan[target] = Loan({initial_debt: final_debt, rate_mul: rate_mul})
    if final_debt == 0:
        log UserState(target, 0, 0, 0, 0, 0)  # Not logging partial removeal b/c we have not enough info
        self._remove_from_list(target)


    debt_adjustment: int256 = self._decrease_total_debt(debt, rate_mul)

    return debt_adjustment, debt, xy


@view
@external
@nonreentrant('lock')
def tokens_to_liquidate(account: address, frac: uint256 = 10 ** 18) -> uint256:
    """
    @notice Calculate the amount of stablecoins to have in liquidator's wallet to liquidate a account
    @param account Address of the account to liquidate
    @param frac Fraction to liquidate; 100% = 10**18
    @return The amount of stablecoins needed
    """
    health_limit: uint256 = 0
    if account != msg.sender:
        health_limit = self.liquidation_discounts[account]
    stablecoins: uint256 = unsafe_div(AMM.get_sum_xy(account)[0] * self._get_f_remove(frac, health_limit), 10 ** 18)
    debt: uint256 = unsafe_div(self._debt(account)[0] * frac, 10 ** 18)

    return unsafe_sub(max(debt, stablecoins), stablecoins)


@view
@external
@nonreentrant('lock')
def health(account: address, full: bool = False) -> int256:
    """
    @notice Returns position health normalized to 1e18 for the account.
            Liquidation starts when < 0, however devaluation of collateral doesn't cause liquidation
    """
    return self._health(account, self._debt(account)[0], full, self.liquidation_discounts[account])


@view
@external
@nonreentrant('lock')
def users_to_liquidate(_from: uint256=0, _limit: uint256=0) -> DynArray[Position, 1000]:
    """
    @notice Returns a dynamic array of users who can be "hard-liquidated".
            This method is designed for convenience of liquidation bots.
    @param _from Loan index to start iteration from
    @param _limit Number of loans to look over
    @return Dynamic array with detailed info about positions of users
    """
    n_loans: uint256 = self.n_loans
    limit: uint256 = _limit
    if _limit == 0:
        limit = n_loans
    ix: uint256 = _from
    out: DynArray[Position, 1000] = []
    for i in range(10**6):
        if ix >= n_loans or i == limit:
            break
        account: address = self.loans[ix]
        debt: uint256 = self._debt(account)[0]
        health: int256 = self._health(account, debt, True, self.liquidation_discounts[account])
        if health < 0:
            xy: uint256[2] = AMM.get_sum_xy(account)
            out.append(Position({
                account: account,
                x: xy[0],
                y: xy[1],
                debt: debt,
                health: health
            }))
        ix += 1
    return out


# AMM has a nonreentrant decorator
@view
@external
def amm_price() -> uint256:
    """
    @notice Current price from the AMM
    """
    return AMM.get_p()


@view
@external
@nonreentrant('lock')
def user_prices(account: address) -> uint256[2]:  # Upper, lower
    """
    @notice Lowest price of the lower band and highest price of the upper band the account has deposit in the AMM
    @param account User address
    @return (upper_price, lower_price)
    """
    assert AMM.has_liquidity(account)
    ns: int256[2] = AMM.read_user_tick_numbers(account) # ns[1] > ns[0]
    return [AMM.p_oracle_up(ns[0]), AMM.p_oracle_down(ns[1])]


@view
@external
@nonreentrant('lock')
def user_state(account: address) -> uint256[4]:
    """
    @notice Return the account state in one call
    @param account User to return the state for
    @return (collateral, stablecoin, debt, N)
    """
    xy: uint256[2] = AMM.get_sum_xy(account)
    ns: int256[2] = AMM.read_user_tick_numbers(account) # ns[1] > ns[0]
    return [xy[1], xy[0], self._debt(account)[0], convert(unsafe_add(unsafe_sub(ns[1], ns[0]), 1), uint256)]


# AMM has nonreentrant decorator
@external
def set_amm_fee(fee: uint256):
    """
    @notice Set the AMM fee (factory admin only)
    @param fee The fee which should be no higher than MAX_FEE
    """
    assert msg.sender == CORE_OWNER.owner()
    assert fee <= MAX_FEE and fee >= MIN_FEE, "Fee"
    AMM.set_fee(fee)


# AMM has nonreentrant decorator
@external
def set_amm_admin_fee(fee: uint256):
    """
    @notice Set AMM's admin fee
    @param fee New admin fee (not higher than MAX_ADMIN_FEE)
    """
    assert msg.sender == CORE_OWNER.owner()
    assert fee <= MAX_ADMIN_FEE, "High fee"
    AMM.set_admin_fee(fee)


@nonreentrant('lock')
@external
def set_borrowing_discounts(loan_discount: uint256, liquidation_discount: uint256):
    """
    @notice Set discounts at which we can borrow (defines max LTV) and where bad liquidation starts
    @param loan_discount Discount which defines LTV
    @param liquidation_discount Discount where bad liquidation starts
    """
    assert msg.sender == CORE_OWNER.owner()
    assert loan_discount > liquidation_discount
    assert liquidation_discount >= MIN_LIQUIDATION_DISCOUNT
    assert loan_discount <= MAX_LOAN_DISCOUNT
    self.liquidation_discount = liquidation_discount
    self.loan_discount = loan_discount
    log SetBorrowingDiscounts(loan_discount, liquidation_discount)


@external
@nonreentrant('lock')
def set_liquidity_mining_hook(hook: address):
    """
    @notice Set liquidity mining callback
    """
    assert msg.sender == CORE_OWNER.owner()
    AMM.set_liquidity_mining_hook(hook)


@nonreentrant('lock')
@external
def set_debt_ceiling(debt_ceiling: uint256):
    """
    @notice Set debt ceiling
    @param debt_ceiling New debt ceiling
    """
    assert msg.sender == CORE_OWNER.owner()
    self.debt_ceiling = debt_ceiling


@external
@nonreentrant('lock')
def collect_fees() -> (uint256, uint256[2]):
    """
    @notice Collect the fees charged as interest
    """
    assert msg.sender == FACTORY

    # AMM-based fees
    xy: uint256[2] = AMM.reset_admin_fees()

    # Borrowing-based fees
    # Total debt increases here, but we intentionally do not enforce `debt_ceiling`
    rate_mul: uint256 = AMM.get_rate_mul()
    debt_increase: uint256 = self._increase_total_debt(0, rate_mul)

    return debt_increase, xy
