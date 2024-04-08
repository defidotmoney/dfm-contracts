# @version 0.3.10
"""
@title CDP Main Controller
@author Curve.Fi (with edits by defidotmoney)
@license Copyright (c) Curve.Fi, 2020-2023 - all rights reserved
"""

interface ERC20:
    def mint(_to: address, _value: uint256) -> bool: nonpayable
    def burn(_to: address, _value: uint256) -> bool: nonpayable
    def transferFrom(_from: address, _to: address, _value: uint256) -> bool: nonpayable
    def transfer(_to: address, _value: uint256) -> bool: nonpayable
    def decimals() -> uint256: view
    def approve(_spender: address, _value: uint256) -> bool: nonpayable
    def balanceOf(_from: address) -> uint256: view

interface PriceOracle:
    def price() -> uint256: view
    def price_w() -> uint256: nonpayable

interface AMM:
    def set_exchange_hook(hook: address) -> bool: nonpayable
    def set_rate(rate: uint256) -> uint256: nonpayable

interface MarketOperator:
    def total_debt() -> uint256: view
    def pending_debt() -> uint256: view
    def max_borrowable(collateral: uint256, N: uint256) -> uint256: view
    def minted() -> uint256: view
    def redeemed() -> uint256: view
    def collect_fees() -> (uint256, uint256[2]): nonpayable
    def set_debt_ceiling(ceiling: uint256) -> bool: nonpayable
    def create_loan(account: address, coll_amount: uint256, debt_amount: uint256, num_bands: uint256) -> uint256: nonpayable
    def adjust_loan(account: address, coll_amount: int256, debt_amount: int256, max_active_band: int256) -> int256: nonpayable
    def close_loan(account: address) -> (int256, uint256, uint256[2]): nonpayable
    def liquidate(caller: address, target: address, min_x: uint256, frac: uint256) -> (int256, uint256, uint256[2]): nonpayable
    def AMM() -> address: view

interface MonetaryPolicy:
    def rate_write(market: address) -> uint256: nonpayable

interface PegKeeper:
    def set_regulator(regulator: address): nonpayable

interface PegKeeperRegulator:
    def max_debt() -> uint256: view
    def owed_debt() -> uint256: view
    def active_debt() -> uint256: view
    def recall_debt(amount: uint256): nonpayable
    def get_peg_keepers_with_debt_ceilings() -> (DynArray[PegKeeper, 256], DynArray[uint256, 256]): view
    def init_migrate_peg_keepers(peg_keepers: DynArray[PegKeeper, 256], debt_ceilings: DynArray[uint256, 256]): nonpayable

interface CoreOwner:
    def owner() -> address: view
    def stableCoin() -> ERC20: view
    def feeReceiver() -> address: view

interface ControllerHooks:
    def on_create_loan(account: address, market: address, coll_amount: uint256, debt_amount: uint256) -> int256: nonpayable
    def on_adjust_loan(account: address, market: address, coll_change: int256, debt_changet: int256) -> int256: nonpayable
    def on_close_loan(account: address, market: address, account_debt: uint256) -> int256: nonpayable
    def on_liquidation(caller: address, market: address, target: address, debt_liquidated: uint256) -> int256: nonpayable

interface AmmHooks:
    def before_collateral_out(amount: uint256): nonpayable
    def after_collateral_in(amount: uint256): nonpayable


event AddMarket:
    collateral: indexed(address)
    market: address
    amm: address
    mp_idx: uint256

event SetDelegateApproval:
    account: indexed(address)
    delegate: indexed(address)
    is_approved: bool

event SetImplementations:
    amm: address
    market: address

event SetMarketHooks:
    market: indexed(address)
    hooks: indexed(address)
    active_hooks: bool[NUM_HOOK_IDS]

event SetAmmHooks:
    market: indexed(address)
    hooks: indexed(address)

event AddMonetaryPolicy:
    mp_idx: indexed(uint256)
    monetary_policy: address

event ChangeMonetaryPolicy:
    mp_idx: indexed(uint256)
    monetary_policy: address

event ChangeMonetaryPolicyForMarket:
    market: indexed(address)
    mp_idx: indexed(uint256)

event SetGlobalMarketDebtCeiling:
    debt_ceiling: uint256

event SetPegKeeperRegulator:
    regulator: address
    with_migration: bool

event CreateLoan:
    market: indexed(address)
    account: indexed(address)
    coll_amount: uint256
    debt_amount: uint256

event AdjustLoan:
    market: indexed(address)
    account: indexed(address)
    coll_adjustment: int256
    debt_adjustment: int256

event CloseLoan:
    market: indexed(address)
    account: indexed(address)
    coll_withdrawn: uint256
    debt_withdrawn: uint256
    debt_repaid: uint256

event LiquidateLoan:
    market: indexed(address)
    liquidator: indexed(address)
    account: indexed(address)
    coll_received: uint256
    debt_received: uint256
    debt_repaid: uint256

event CollectAmmFees:
    market: indexed(address)
    amm_coll_fees: uint256
    amm_debt_fees: uint256

event CollectFees:
    minted: uint256
    redeemed: uint256
    total_debt: uint256
    fee: uint256


struct MarketContracts:
    collateral: address
    amm: address
    mp_idx: uint256


enum HookId:
    ON_CREATE_LOAN
    ON_ADJUST_LOAN
    ON_CLOSE_LOAN
    ON_LIQUIDATION


NUM_HOOK_IDS: constant(uint256) = 4

# Limits
MIN_A: constant(uint256) = 2
MAX_A: constant(uint256) = 10000
MIN_FEE: constant(uint256) = 10**6  # 1e-12, still needs to be above 0
MAX_FEE: constant(uint256) = 10**17  # 10%
MAX_ADMIN_FEE: constant(uint256) = 10**18  # 100%
MAX_LOAN_DISCOUNT: constant(uint256) = 5 * 10**17
MIN_LIQUIDATION_DISCOUNT: constant(uint256) = 10**16
MAX_ACTIVE_BAND: constant(int256) = max_value(int256)

STABLECOIN: public(immutable(ERC20))
CORE_OWNER: public(immutable(CoreOwner))
market_operator_implementation: public(address)
amm_implementation: public(address)
peg_keeper_regulator: public(PegKeeperRegulator)

collateral_markets: HashMap[address, DynArray[address, 256]]
market_contracts: public(HashMap[address, MarketContracts])
monetary_policies: public(address[256])
n_monetary_policies: public(uint256)

global_market_debt_ceiling: public(uint256)
total_debt: public(uint256)
minted: public(uint256)
redeemed: public(uint256)

isApprovedDelegate: public(HashMap[address, HashMap[address, bool]])

global_hooks: uint256
market_hooks: HashMap[address, uint256]
amm_hooks: HashMap[address, address]


@external
def __init__(
    core: CoreOwner,
    stable: ERC20,
    market_impl: address,
    amm_impl: address,
    monetary_policies: DynArray[address, 10],
    debt_ceiling: uint256
):
    CORE_OWNER = core
    STABLECOIN = stable

    self.market_operator_implementation = market_impl
    self.amm_implementation = amm_impl
    log SetImplementations(amm_impl, market_impl)

    idx: uint256 = 0
    for mp in monetary_policies:
        self.monetary_policies[idx] = mp
        idx += 1
    self.n_monetary_policies = idx

    self.global_market_debt_ceiling = debt_ceiling
    log SetGlobalMarketDebtCeiling(debt_ceiling)


# --- external view functions ---

@view
@external
def owner() -> address:
    return CORE_OWNER.owner()


@view
@external
def get_market(collateral: address, i: uint256 = 0) -> address:
    """
    @notice Get market address for collateral
    @dev Returns empty(address) if market does not exist
    @param collateral Address of collateral token
    @param i Iterate over several markets for collateral if needed
    """
    if i > len(self.collateral_markets[collateral]):
        return empty(address)
    return self.collateral_markets[collateral][i]


@view
@external
def get_amm(collateral: address, i: uint256 = 0) -> address:
    """
    @notice Get AMM address for collateral
    @dev Returns empty(address) if market does not exist
    @param collateral Address of collateral token
    @param i Iterate over several amms for collateral if needed
    """
    if i > len(self.collateral_markets[collateral]):
        return empty(address)
    market: address = self.collateral_markets[collateral][i]
    return self.market_contracts[market].amm


@view
@external
def get_hooks(market: address) -> (address, address, bool[NUM_HOOK_IDS]):
    """
    @notice Get the hook contracts and active hooks for the given market
    @param market Market address. Set as empty(address) for global hooks.
    @return (amm hooks, market hooks, active market hooks boolean array)
    """
    hookdata: uint256 = 0
    if market == empty(address):
        hookdata = self.global_hooks
    else:
        hookdata = self.market_hooks[market]

    hook: address = convert(hookdata >> 96, address)

    active_hooks: bool[NUM_HOOK_IDS] = empty(bool[NUM_HOOK_IDS])
    if hook != empty(address):
        for i in range(NUM_HOOK_IDS):
            if hookdata >> i & 1 == 0:
                continue
            active_hooks[i] = True

    return self.amm_hooks[market], hook, active_hooks


@view
@external
def get_monetary_policy_for_market(market: address) -> address:
    c: MarketContracts = self.market_contracts[market]

    if c.collateral == empty(address):
        return empty(address)

    return self.monetary_policies[c.mp_idx]


@view
@external
def peg_keeper_debt() -> uint256:
    regulator: PegKeeperRegulator = self.peg_keeper_regulator
    if regulator.address == empty(address):
        return 0
    return regulator.active_debt()


@view
@external
def max_borrowable(market: MarketOperator, coll_amount: uint256, N: uint256) -> uint256:
    debt_ceiling: uint256 = self.global_market_debt_ceiling
    total_debt: uint256 = self.total_debt + market.pending_debt()
    if total_debt >= debt_ceiling:
        return 0

    global_max: uint256 = debt_ceiling - total_debt
    market_max: uint256 = market.max_borrowable(coll_amount, N)

    return min(global_max, market_max)


@view
@external
def stored_admin_fees() -> uint256:
    """
    @notice Calculate the amount of fees obtained from the interest
    """
    return self.total_debt + self.redeemed - self.minted


# --- unguarded nonpayable functions ---

@external
def setDelegateApproval(delegate: address, is_approved: bool):
    """
    @dev Functions that supports delegation include an `account` input allowing
         the delegated caller to indicate who they are calling on behalf of.
         In executing the call, all internal state updates are applied for
         `account` and all value transfers occur to or from the caller.

        For example: a delegated call to `create_loan` will transfer collateral
        from the caller, create the debt position for `account`, and send newly
        minted stablecoins to the caller.
    """
    self.isApprovedDelegate[msg.sender][delegate] = is_approved
    log SetDelegateApproval(msg.sender, delegate, is_approved)


@external
@nonreentrant('lock')
def create_loan(account: address, market: address, coll_amount: uint256, debt_amount: uint256, n_bands: uint256):
    assert coll_amount > 0 and debt_amount > 0
    self._assert_caller_or_approved_delegate(account)
    c: MarketContracts = self._get_contracts(market)

    hook_adjust: int256 = self._call_hooks(
        market,
        HookId.ON_CREATE_LOAN,
        _abi_encode(
            account,
            market,
            coll_amount,
            debt_amount,
            method_id=method_id("on_create_loan(address,address,uint256,uint256)")
        )
    )
    debt_amount_final: uint256 = self._uint_plus_int(debt_amount, hook_adjust)

    self._deposit_collateral(msg.sender, c.collateral, c.amm, coll_amount)
    debt_increase: uint256 = MarketOperator(market).create_loan(account, coll_amount, debt_amount_final, n_bands)
    self._update_rate(market, c.amm, c.mp_idx)

    total_debt: uint256 = self.total_debt + debt_increase
    self._assert_below_debt_ceiling(total_debt)

    self.total_debt = total_debt
    self.minted += debt_amount

    STABLECOIN.mint(msg.sender, debt_amount)

    log CreateLoan(market, account, coll_amount, debt_amount_final)


@external
@nonreentrant('lock')
def adjust_loan(account: address, market: address, coll_change: int256, debt_change: int256, max_active_band: int256 = max_value(int256)):
    assert coll_change != 0 or debt_change != 0

    self._assert_caller_or_approved_delegate(account)
    c: MarketContracts = self._get_contracts(market)

    debt_change_final: int256 = self._call_hooks(
        market,
        HookId.ON_ADJUST_LOAN,
        _abi_encode(
            account,
            market,
            coll_change,
            debt_change,
            method_id=method_id("on_adjust_loan(address,address,int256,int256)")
        )
    ) + debt_change

    debt_adjustment: int256 = MarketOperator(market).adjust_loan(account, coll_change, debt_change_final, max_active_band)
    self._update_rate(market, c.amm, c.mp_idx)

    total_debt: uint256 = self._uint_plus_int(self.total_debt, debt_adjustment)
    self.total_debt = total_debt

    if debt_change != 0:
        debt_change_abs: uint256 = convert(abs(debt_change), uint256)
        if debt_change > 0:
            self._assert_below_debt_ceiling(total_debt)
            self.minted += debt_change_abs
            STABLECOIN.mint(msg.sender, debt_change_abs)
        else:
            self.redeemed += debt_change_abs
            STABLECOIN.burn(msg.sender, debt_change_abs)

    if coll_change != 0:
        coll_change_abs: uint256 = convert(abs(coll_change), uint256)
        if coll_change > 0:
            self._deposit_collateral(msg.sender, c.collateral, c.amm, coll_change_abs)
        else:
            self._withdraw_collateral(msg.sender, c.collateral, c.amm, coll_change_abs)

    log AdjustLoan(market, account, coll_change, debt_change_final)


@external
@nonreentrant('lock')
def close_loan(account: address, market: address):
    self._assert_caller_or_approved_delegate(account)
    c: MarketContracts = self._get_contracts(market)

    debt_adjustment: int256 = 0
    burn_amount: uint256 = 0
    xy: uint256[2] = empty(uint256[2])
    debt_adjustment, burn_amount, xy = MarketOperator(market).close_loan(account)
    self._update_rate(market, c.amm, c.mp_idx)

    burn_adjust: int256 = self._call_hooks(
        market,
        HookId.ON_CLOSE_LOAN,
        _abi_encode(account, market, burn_amount, method_id=method_id("on_close_loan(address,address,uint256)"))
    )
    burn_amount = self._uint_plus_int(burn_amount, burn_adjust)

    self.redeemed += burn_amount
    self.total_debt = self._uint_plus_int(self.total_debt, debt_adjustment)

    if xy[0] > 0:
        STABLECOIN.transferFrom(c.amm, msg.sender, xy[0])
    STABLECOIN.burn(msg.sender, burn_amount)
    if xy[1] > 0:
        self._withdraw_collateral(msg.sender, c.collateral, c.amm, xy[1])

    log CloseLoan(market, account, xy[1], xy[0], burn_amount)


@external
@nonreentrant('lock')
def liquidate(market: address, target: address, min_x: uint256, frac: uint256 = 10**18):
    assert frac <= 10**18
    c: MarketContracts = self._get_contracts(market)

    debt_adjustment: int256 = 0
    debt_amount: uint256 = 0
    xy: uint256[2] = empty(uint256[2])
    debt_adjustment, debt_amount, xy = MarketOperator(market).liquidate(msg.sender, target, min_x, frac)
    self._update_rate(market, c.amm, c.mp_idx)

    burn_adjust: int256 = self._call_hooks(
        market,
        HookId.ON_LIQUIDATION,
        _abi_encode(
            msg.sender,
            market,
            target,
            debt_amount,
            method_id=method_id("on_liquidation(address,address,address,uint256)")
        )
    )
    debt_amount = self._uint_plus_int(debt_amount, burn_adjust)

    self.redeemed += debt_amount
    self.total_debt = self._uint_plus_int(self.total_debt, debt_adjustment)

    burn_amm: uint256 = min(xy[0], debt_amount)
    if burn_amm != 0:
        STABLECOIN.burn(c.amm, burn_amm)

    if debt_amount > xy[0]:
        remaining: uint256 = unsafe_sub(debt_amount, xy[0])
        STABLECOIN.burn(msg.sender, remaining)
    elif xy[0] > debt_amount:
        STABLECOIN.transferFrom(c.amm, msg.sender, unsafe_sub(xy[0], debt_amount))

    if xy[1] > 0:
        self._withdraw_collateral(msg.sender, c.collateral, c.amm, xy[1])

    log LiquidateLoan(market, msg.sender, target, xy[1], xy[0], debt_amount)


@external
@nonreentrant('lock')
def collect_fees(market_list: DynArray[address, 255]) -> uint256:
    receiver: address = CORE_OWNER.feeReceiver()

    debt_increase_total: uint256 = 0
    for market in market_list:
        c: MarketContracts = self._get_contracts(market)

        debt_increase: uint256 = 0
        xy: uint256[2] = empty(uint256[2])

        debt_increase, xy = MarketOperator(market).collect_fees()
        self._update_rate(market, c.amm, c.mp_idx)
        debt_increase_total += debt_increase

        if xy[0] > 0:
            STABLECOIN.transferFrom(c.amm, receiver, xy[0])
        if xy[1] > 0:
            self._withdraw_collateral(receiver, c.collateral, c.amm, xy[1])

        log CollectAmmFees(market, xy[1], xy[0])

    total_debt: uint256 = self.total_debt + debt_increase_total
    self.total_debt = total_debt

    mint_total: uint256 = 0
    minted: uint256 = self.minted
    redeemed: uint256 = self.redeemed
    to_be_redeemed: uint256 = total_debt + redeemed

    # Difference between to_be_redeemed and minted amount is exactly due to interest charged
    if to_be_redeemed > minted:
        self.minted = to_be_redeemed
        mint_total = unsafe_sub(to_be_redeemed, minted)  # Now this is the fees to charge
        STABLECOIN.mint(receiver, mint_total)

    log CollectFees(minted, redeemed, total_debt, mint_total)
    return mint_total


# --- owner-only nonpayable functions ---

@external
@nonreentrant('lock')
def add_market(token: address, A: uint256, fee: uint256, admin_fee: uint256, oracle: PriceOracle,
               mp_idx: uint256, loan_discount: uint256, liquidation_discount: uint256,
               debt_ceiling: uint256) -> address[2]:
    """
    @notice Add a new market, creating an AMM and a MarketOperator from a blueprint
    @param token Collateral token address
    @param A Amplification coefficient; one band size is 1/A
    @param fee AMM fee in the market's AMM
    @param admin_fee AMM admin fee
    @param oracle Address of price oracle contract for this market
    @param mp_idx Monetary policy index for this market
    @param loan_discount Loan discount: allowed to borrow only up to x_down * (1 - loan_discount)
    @param liquidation_discount Discount which defines a bad liquidation threshold
    @param debt_ceiling Debt ceiling for this market
    @return (MarketOperator, AMM)
    """
    self._assert_only_owner()
    assert A >= MIN_A and A <= MAX_A, "Wrong A"
    assert fee <= MAX_FEE, "Fee too high"
    assert fee >= MIN_FEE, "Fee too low"
    assert admin_fee < MAX_ADMIN_FEE, "Admin fee too high"
    assert liquidation_discount >= MIN_LIQUIDATION_DISCOUNT, "Liquidation discount too low"
    assert loan_discount <= MAX_LOAN_DISCOUNT, "Loan discount too high"
    assert loan_discount > liquidation_discount, "need loan_discount>liquidation_discount"
    assert mp_idx < self.n_monetary_policies, "Invalid monetary policy index"

    p: uint256 = oracle.price()
    assert p > 0
    assert oracle.price_w() == p

    market: address = create_from_blueprint(
        self.market_operator_implementation,
        CORE_OWNER.address,
        token,
        self.amm_implementation,
        debt_ceiling,
        loan_discount,
        liquidation_discount,
        A,
        p,
        fee,
        admin_fee,
        oracle,
        code_offset=3
    )
    # `AMM` is deployed in constructor of `MarketOperator`
    amm: address = MarketOperator(market).AMM()

    self.collateral_markets[token].append(market)
    self.market_contracts[market] = MarketContracts({collateral: token, amm: amm, mp_idx: mp_idx})

    log AddMarket(token, market, amm, mp_idx)
    return [market, amm]


@external
def set_global_market_debt_ceiling(debt_ceiling: uint256):
    self._assert_only_owner()
    self.global_market_debt_ceiling = debt_ceiling

    log SetGlobalMarketDebtCeiling(debt_ceiling)


@external
def set_implementations(market: address, amm: address):
    """
    @notice Set new implementations (blueprints) for market and amm
    @dev Already-deployed markets are unaffected by this change
    @param market Address of the market blueprint
    @param amm Address of the AMM blueprint
    """
    self._assert_only_owner()
    assert market != empty(address)
    assert amm != empty(address)
    self.market_operator_implementation = market
    self.amm_implementation = amm
    log SetImplementations(amm, market)


@external
def set_market_hooks(market: address, hooks: address, active_hooks: bool[NUM_HOOK_IDS]):
    """
    @notice Set callback hooks for `market`
    @param market Market to set hooks for. Set as empty(address) for global hooks.
    @param hooks Address of hooks contract to set as active. Set to empty(address) to disable all hooks.
    @param active_hooks Array of booleans where items map to the values in the `HookId` enum.
    """
    self._assert_only_owner()

    hookdata: uint256 = (convert(hooks, uint256) << 96)
    if hooks != empty(address):
        for i in range(NUM_HOOK_IDS):
            if active_hooks[i]:
                hookdata += 1 << i

    if market == empty(address):
        self.global_hooks = hookdata
    else:
        self.market_hooks[market] = hookdata

    log SetMarketHooks(market, hooks, active_hooks)


@external
def set_amm_hook(market: address, hook: address):
    self._assert_only_owner()
    amm: address = self._get_contracts(market).amm
    AMM(amm).set_exchange_hook(hook)
    self.amm_hooks[amm] = hook

    log SetAmmHooks(market, hook)


@external
def add_new_monetary_policy(monetary_policy: address):
    self._assert_only_owner()
    idx: uint256 = self.n_monetary_policies
    self.monetary_policies[idx] = monetary_policy
    self.n_monetary_policies = idx +1

    log AddMonetaryPolicy(idx, monetary_policy)


@external
def change_existing_monetary_policy(monetary_policy: address, mp_idx: uint256):
    self._assert_only_owner()
    assert mp_idx < self.n_monetary_policies
    self.monetary_policies[mp_idx] = monetary_policy

    log ChangeMonetaryPolicy(mp_idx, monetary_policy)


@external
def change_market_monetary_policy(market: address, mp_idx: uint256):
    self._assert_only_owner()
    assert mp_idx < self.n_monetary_policies
    self.market_contracts[market].mp_idx = mp_idx

    log ChangeMonetaryPolicyForMarket(market, mp_idx)


@external
def set_peg_keeper_regulator(regulator: PegKeeperRegulator, with_migration: bool):
    """
    @notice Set the active peg keeper regulator
    @dev The regulator must also be given permission to mint `STABLECOIN`
    @param regulator Address of the new peg keeper regulator. Can also be set to
                     empty(address) to have no active regulator.
    @param with_migration if True, all peg keepers from the old regulator are
                          added to the new regulator with the same debt ceilings.
    """
    self._assert_only_owner()
    old: PegKeeperRegulator = self.peg_keeper_regulator
    assert old != regulator

    if with_migration:
        peg_keepers: DynArray[PegKeeper, 256] = []
        debt_ceilings: DynArray[uint256, 256] = []
        (peg_keepers, debt_ceilings) = old.get_peg_keepers_with_debt_ceilings()
        for pk in peg_keepers:
            pk.set_regulator(regulator.address)
        regulator.init_migrate_peg_keepers(peg_keepers, debt_ceilings)

    self.peg_keeper_regulator = regulator

    log SetPegKeeperRegulator(regulator.address, with_migration)


# --- internal functions ---

@view
@internal
def _assert_only_owner():
    assert msg.sender == CORE_OWNER.owner(), "MainController: Only owner"


@view
@internal
def _assert_caller_or_approved_delegate(account: address):
    if msg.sender != account:
        assert self.isApprovedDelegate[account][msg.sender], "Delegate not approved"


@view
@internal
def _assert_below_debt_ceiling(total_debt: uint256):
    assert total_debt <= self.global_market_debt_ceiling, "Exceeds global debt ceiling"


@pure
@internal
def _uint_plus_int(initial: uint256, adjustment: int256) -> uint256:
    if adjustment < 0:
        return initial - convert(-adjustment, uint256)
    else:
        return initial + convert(adjustment, uint256)


@view
@internal
def _get_contracts(market: address) -> MarketContracts:
    c: MarketContracts = self.market_contracts[market]

    assert c.collateral != empty(address), "Invalid market"

    return c


@internal
def _deposit_collateral(account: address, collateral: address, amm: address, amount: uint256):
    assert ERC20(collateral).transferFrom(account, amm, amount, default_return_value=True)

    hooks: address = self.amm_hooks[amm]
    if hooks != empty(address):
        AmmHooks(hooks).after_collateral_in(amount)



@internal
def _withdraw_collateral(account: address, collateral: address, amm: address, amount: uint256):
    hooks: address = self.amm_hooks[amm]
    if hooks != empty(address):
        AmmHooks(hooks).before_collateral_out(amount)

    assert ERC20(collateral).transferFrom(amm, account, amount, default_return_value=True)


@internal
def _call_hook(hookdata: uint256, hook_id: HookId, calldata: Bytes[255]) -> int256:
    if hookdata & convert(hook_id, uint256) == 0:
        return 0
    hook: address = convert(hookdata >> 96, address)
    return convert(raw_call(hook, calldata, max_outsize=32), int256)


@internal
def _call_hooks(market: address, hook_id: HookId, calldata: Bytes[255]) -> int256:
    debt_adjustment: int256 = 0

    debt_adjustment += self._call_hook(self.market_hooks[market], hook_id, calldata)
    debt_adjustment += self._call_hook(self.global_hooks, hook_id, calldata)

    return debt_adjustment


@internal
def _update_rate(market: address, amm: address, mp_idx: uint256):
    mp_rate: uint256 = MonetaryPolicy(self.monetary_policies[mp_idx]).rate_write(market)
    AMM(amm).set_rate(mp_rate)
