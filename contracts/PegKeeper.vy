# @version 0.3.10
"""
@title Peg Keeper V2
@license MIT
@author Curve.Fi
@notice Peg Keeper
@dev Version 2
"""

interface Regulator:
    def stablecoin() -> address: view
    def provide_allowed(_pk: address=msg.sender) -> uint256: view
    def withdraw_allowed(_pk: address=msg.sender) -> uint256: view

interface CurvePool:
    def balances(i_coin: uint256) -> uint256: view
    def coins(i: uint256) -> address: view
    def calc_token_amount(_amounts: uint256[2], _is_deposit: bool) -> uint256: view
    def add_liquidity(_amounts: uint256[2], _min_mint_amount: uint256) -> uint256: nonpayable
    def remove_liquidity_imbalance(_amounts: uint256[2], _max_burn_amount: uint256) -> uint256: nonpayable
    def get_virtual_price() -> uint256: view
    def balanceOf(arg0: address) -> uint256: view
    def transfer(_to: address, _value: uint256) -> bool: nonpayable

interface ERC20:
    def approve(_spender: address, _amount: uint256): nonpayable
    def balanceOf(_owner: address) -> uint256: view
    def decimals() -> uint256: view
    def transfer(receiver: address, amount: uint256) -> bool: nonpayable
    def burn(target: address, amount: uint256) -> bool: nonpayable

interface CoreOwner:
    def owner() -> address: view
    def stableCoin() -> ERC20: view
    def feeReceiver() -> address: view


event Provide:
    amount: uint256

event Withdraw:
    amount: uint256

event Profit:
    lp_amount: uint256

event SetNewCallerShare:
    caller_share: uint256

event SetNewRegulator:
    regulator: address

event RecallDebt:
    recalled: uint256
    burned: uint256
    owing: uint256


# Time between providing/withdrawing coins
ACTION_DELAY: constant(uint256) = 15 * 60
ADMIN_ACTIONS_DELAY: constant(uint256) = 3 * 86400

PRECISION: constant(uint256) = 10 ** 18

CORE_OWNER: public(immutable(CoreOwner))
CONTROLLER: public(immutable(address))
POOL: public(immutable(CurvePool))
I: immutable(uint256)  # index of pegged in pool
PEGGED: public(immutable(ERC20))
IS_INVERSE: public(immutable(bool))
PEG_MUL: immutable(uint256)

regulator: public(Regulator)

last_change: public(uint256)
debt: public(uint256)
owed_debt: public(uint256)

SHARE_PRECISION: constant(uint256) = 10 ** 5
caller_share: public(uint256)


@external
def __init__(core: CoreOwner, regulator: Regulator, controller: address, stable: ERC20, pool: CurvePool, caller_share: uint256):
    """
    @notice Contract constructor
    @param regulator Peg Keeper Regulator
    @param pool Contract pool address
    @param caller_share Caller's share of profit
    """
    CORE_OWNER = core
    POOL = pool
    CONTROLLER = controller
    PEGGED = stable
    stable.approve(pool.address, max_value(uint256))

    coins: ERC20[2] = [ERC20(pool.coins(0)), ERC20(pool.coins(1))]
    for i in range(2):
        if coins[i] == stable:
            I = i
            IS_INVERSE = (i == 0)
        else:
            PEG_MUL = 10 ** (18 - coins[i].decimals())

    self.regulator = regulator
    log SetNewRegulator(regulator.address)

    assert caller_share <= SHARE_PRECISION  # dev: bad part value
    self.caller_share = caller_share
    log SetNewCallerShare(caller_share)


@view
@external
def owner() -> address:
    return CORE_OWNER.owner()


@view
@internal
def _assert_only_regulator():
    assert msg.sender == self.regulator.address, "PegKeeper: Only regulator"


@internal
def _burn_owed_debt():
    owed_debt: uint256 = self.owed_debt
    if owed_debt > 0:
        debt_reduce: uint256 = min(owed_debt, PEGGED.balanceOf(self))
        if debt_reduce > 0:
            PEGGED.burn(self, debt_reduce)
            owed_debt -= debt_reduce
            self.owed_debt = owed_debt
            log RecallDebt(0, debt_reduce, owed_debt)

@internal
def _provide(_amount: uint256) -> int256:
    """
    @notice Implementation of provide
    @dev Coins should be already in the contract
    """
    if _amount == 0:
        return 0

    self._burn_owed_debt()

    amount: uint256 = min(_amount, PEGGED.balanceOf(self))

    amounts: uint256[2] = empty(uint256[2])
    amounts[I] = amount
    POOL.add_liquidity(amounts, 0)

    self.last_change = block.timestamp
    self.debt += amount
    log Provide(amount)

    return convert(amount, int256)


@internal
def _withdraw(_amount: uint256) -> int256:
    """
    @notice Implementation of withdraw
    """
    if _amount == 0:
        return 0

    debt: uint256 = self.debt
    amount: uint256 = min(_amount, debt)

    amounts: uint256[2] = empty(uint256[2])
    amounts[I] = amount
    POOL.remove_liquidity_imbalance(amounts, max_value(uint256))

    self.last_change = block.timestamp
    self.debt = debt - amount

    self._burn_owed_debt()

    log Withdraw(amount)

    return -convert(amount, int256)


@internal
@pure
def _calc_profit_from(lp_balance: uint256, virtual_price: uint256, debt: uint256) -> uint256:
    """
    @notice PegKeeper's profit calculation formula
    """
    lp_debt: uint256 = debt * PRECISION / virtual_price

    if lp_balance <= lp_debt:
        return 0
    else:
        return lp_balance - lp_debt


@internal
@view
def _calc_profit() -> uint256:
    """
    @notice Calculate PegKeeper's profit using current values
    """
    return self._calc_profit_from(POOL.balanceOf(self), POOL.get_virtual_price(), self.debt)


@internal
@view
def _calc_call_profit(_amount: uint256, _is_deposit: bool) -> uint256:
    """
    @notice Calculate overall profit from calling update()
    """
    lp_balance: uint256 = POOL.balanceOf(self)
    virtual_price: uint256 = POOL.get_virtual_price()
    debt: uint256 = self.debt
    initial_profit: uint256 = self._calc_profit_from(lp_balance, virtual_price, debt)

    amount: uint256 = _amount
    if _is_deposit:
        amount = min(_amount, PEGGED.balanceOf(self))
    else:
        amount = min(_amount, debt)

    amounts: uint256[2] = empty(uint256[2])
    amounts[I] = amount
    lp_balance_diff: uint256 = POOL.calc_token_amount(amounts, _is_deposit)

    if _is_deposit:
        lp_balance += lp_balance_diff
        debt += amount
    else:
        lp_balance -= lp_balance_diff
        debt -= amount

    new_profit: uint256 = self._calc_profit_from(lp_balance, virtual_price, debt)
    if new_profit <= initial_profit:
        return 0
    return new_profit - initial_profit


@external
@view
def calc_profit() -> uint256:
    """
    @notice Calculate generated profit in LP tokens. Does NOT include already withdrawn profit
    @return Amount of generated profit
    """
    return self._calc_profit()


@external
@view
def estimate_caller_profit() -> uint256:
    """
    @notice Estimate profit from calling update()
    @dev This method is not precise, real profit is always more because of increasing virtual price
    @return Expected amount of profit going to beneficiary
    """
    if self.last_change + ACTION_DELAY > block.timestamp:
        return 0

    balance_pegged: uint256 = POOL.balances(I)
    balance_peg: uint256 = POOL.balances(1 - I) * PEG_MUL

    call_profit: uint256 = 0
    if balance_peg > balance_pegged:
        allowed: uint256 = self.regulator.provide_allowed()
        call_profit = self._calc_call_profit(min((balance_peg - balance_pegged) / 5, allowed), True)  # this dumps stablecoin

    else:
        allowed: uint256 = self.regulator.withdraw_allowed()
        call_profit = self._calc_call_profit(min((balance_pegged - balance_peg) / 5, allowed), False)  # this pumps stablecoin

    return call_profit * self.caller_share / SHARE_PRECISION


@external
@nonpayable
def update(_beneficiary: address) -> (int256, uint256):
    """
    @notice Provide or withdraw coins from the pool to stabilize it
    @dev Called via the regulator
    @param _beneficiary Beneficiary address
    @return (change in peg keeper's debt, profit received by beneficiary)
    """
    self._assert_only_regulator()
    if self.last_change + ACTION_DELAY > block.timestamp:
        return 0, 0

    balance_pegged: uint256 = POOL.balances(I)
    balance_peg: uint256 = POOL.balances(1 - I) * PEG_MUL

    initial_profit: uint256 = self._calc_profit()

    debt_adjustment: int256 = 0
    if balance_peg > balance_pegged:
        allowed: uint256 = self.regulator.provide_allowed()
        assert allowed > 0, "Regulator ban"
        debt_adjustment = self._provide(min(unsafe_sub(balance_peg, balance_pegged) / 5, allowed))  # this dumps stablecoin

    else:
        allowed: uint256 = self.regulator.withdraw_allowed()
        assert allowed > 0, "Regulator ban"
        debt_adjustment = self._withdraw(min(unsafe_sub(balance_pegged, balance_peg) / 5, allowed))  # this pumps stablecoin

    # Send generated profit
    new_profit: uint256 = self._calc_profit()
    assert new_profit > initial_profit, "peg unprofitable"
    lp_amount: uint256 = new_profit - initial_profit
    caller_profit: uint256 = lp_amount * self.caller_share / SHARE_PRECISION
    if caller_profit > 0:
        POOL.transfer(_beneficiary, caller_profit)

    return (debt_adjustment, caller_profit)


@external
@nonpayable
def withdraw_profit() -> uint256:
    """
    @notice Withdraw profit generated by Peg Keeper
    @return Amount of LP Token received
    """
    lp_amount: uint256 = self._calc_profit()
    POOL.transfer(CORE_OWNER.feeReceiver(), lp_amount)

    log Profit(lp_amount)

    return lp_amount


@external
@nonpayable
def set_new_caller_share(_new_caller_share: uint256):
    """
    @notice Set new update caller's part
    @param _new_caller_share Part with SHARE_PRECISION
    """
    assert msg.sender == CORE_OWNER.owner(), "PegKeeper: Only owner"
    assert _new_caller_share <= SHARE_PRECISION  # dev: bad part value

    self.caller_share = _new_caller_share

    log SetNewCallerShare(_new_caller_share)

@external
@nonpayable
def set_regulator(_new_regulator: Regulator):
    """
    @notice Set new peg keeper regulator
    """
    assert msg.sender == CONTROLLER, "PegKeeper: Only controller"
    assert _new_regulator.address != empty(address)  # dev: bad regulator

    self.regulator = _new_regulator
    log SetNewRegulator(_new_regulator.address)


@external
@nonpayable
def recall_debt(amount: uint256) -> uint256:
    self._assert_only_regulator()
    if amount == 0:
        return 0

    debt: uint256 = PEGGED.balanceOf(self)
    burned: uint256 = 0
    owed: uint256 = 0
    if debt >= amount:
        PEGGED.burn(self, amount)
        burned = amount
    else:
        if debt > 0:
            PEGGED.burn(self, debt)
            burned = debt
        owed = self.owed_debt + amount - burned
        self.owed_debt = owed

    log RecallDebt(amount, burned, owed)
    return burned
