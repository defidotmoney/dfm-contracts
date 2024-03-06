# @version 0.3.10
"""
@title crvUSD Main Controller
@author Curve.Fi
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

interface PegKeeperRegulator:
    def max_debt() -> uint256: view
    def owed_debt() -> uint256: view
    def total_debt() -> uint256: view
    def recall_debt(amount: uint256): nonpayable

interface ICoreOwner:
    def owner() -> address: view
    def stableCoin() -> ERC20: view
    def feeReceiver() -> address: view

interface ControllerHooks:
    def on_create_loan(account: address, market: address, coll_amount: uint256, debt_amount: uint256) -> int256: nonpayable
    def on_adjust_loan(account: address, market: address, coll_change: int256, debt_changet: int256) -> int256: nonpayable
    def on_close_loan(account: address, market: address, account_debt: uint256) -> int256: nonpayable
    def on_liquidation(caller: address, market: address, target: address, debt_liquidated: uint256) -> int256: nonpayable

interface AmmHooks:
    def on_add_hook(market: address, amm: address) -> bool: nonpayable
    def on_remove_hook() -> bool: nonpayable
    def before_collateral_out(amount: uint256) -> bool: nonpayable
    def after_collateral_in(amount: uint256) -> bool: nonpayable


event AddMarket:
    collateral: indexed(address)
    market: address
    amm: address
    monetary_policy: address
    ix: uint256

event MintForMarket:
    addr: indexed(address)
    amount: uint256

event RemoveFromMarket:
    addr: indexed(address)
    amount: uint256

event SetImplementations:
    amm: address
    market: address

event CreateLoan:
    market: indexed(address)
    account: indexed(address)
    coll_amount: uint256
    debt_amount: uint256

event AdjustLoan:
    market: indexed(address)
    account: indexed(address)
    coll_increase: uint256
    coll_decrease: uint256
    debt_increase: uint256
    debt_decrease: uint256

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

MAX_MARKETS: constant(uint256) = 50000
MAX_ACTIVE_BAND: constant(int256) = 2**255-1
STABLECOIN: public(immutable(ERC20))
CORE_OWNER: public(immutable(ICoreOwner))
markets: public(address[MAX_MARKETS])
amms: public(address[MAX_MARKETS])
market_operator_implementation: public(address)
amm_implementation: public(address)

n_collaterals: public(uint256)
collaterals: public(address[MAX_MARKETS])
collaterals_index: public(HashMap[address, uint256[1000]])
monetary_policies: public(address[MAX_MARKETS])
n_monetary_policies: public(uint256)

# Limits
MIN_A: constant(uint256) = 2
MAX_A: constant(uint256) = 10000
MIN_FEE: constant(uint256) = 10**6  # 1e-12, still needs to be above 0
MAX_FEE: constant(uint256) = 10**17  # 10%
MAX_ADMIN_FEE: constant(uint256) = 10**18  # 100%
MAX_LOAN_DISCOUNT: constant(uint256) = 5 * 10**17
MIN_LIQUIDATION_DISCOUNT: constant(uint256) = 10**16

market_contracts: public(HashMap[address, MarketContracts])

total_debt: public(uint256)
minted: public(uint256)
redeemed: public(uint256)

isApprovedDelegate: public(HashMap[address, HashMap[address, bool]])

global_hooks: uint256
market_hooks: HashMap[address, uint256]
amm_hooks: HashMap[address, address]

MAX_ETH_GAS: constant(uint256) = 10000  # Forward this much gas to ETH transfers (2300 is what send() does)

peg_keeper_regulator: public(PegKeeperRegulator)
peg_keeper_debt_ceiling: public(uint256)


@external
def __init__(core: ICoreOwner, stable: ERC20, monetary_policies: DynArray[address, 10]):
    CORE_OWNER = core
    STABLECOIN = stable

    idx: uint256 = 0
    for mp in monetary_policies:
        self.monetary_policies[idx] = mp
        idx += 1
    self.n_monetary_policies = idx


@view
@external
def owner() -> address:
    return CORE_OWNER.owner()


@external
def setDelegateApproval(delegate: address, is_approved: bool):
    self.isApprovedDelegate[msg.sender][delegate] = is_approved


@view
@internal
def _assert_caller_or_approved_delegate(account: address):
    if msg.sender != account:
        assert self.isApprovedDelegate[account][msg.sender], "Delegate not approved"


@pure
@internal
def _uint_plus_int(initial: uint256, adjustment: int256) -> uint256:
    if adjustment < 0:
        return initial - convert(-adjustment, uint256)
    else:
        return initial + convert(adjustment, uint256)


@external
@nonreentrant('lock')
def add_market(token: address, A: uint256, fee: uint256, admin_fee: uint256,
               _price_oracle_contract: address,
               mp_idx: uint256, loan_discount: uint256, liquidation_discount: uint256,
               debt_ceiling: uint256) -> address[2]:
    """
    @notice Add a new market, creating an AMM and a MarketOperator from a blueprint
    @param token Collateral token address
    @param A Amplification coefficient; one band size is 1/A
    @param fee AMM fee in the market's AMM
    @param admin_fee AMM admin fee
    @param _price_oracle_contract Address of price oracle contract for this market
    @param mp_idx Monetary policy index for this market
    @param loan_discount Loan discount: allowed to borrow only up to x_down * (1 - loan_discount)
    @param liquidation_discount Discount which defines a bad liquidation threshold
    @param debt_ceiling Debt ceiling for this market
    @return (MarketOperator, AMM)
    """
    assert msg.sender == CORE_OWNER.owner(), "Only admin"
    assert A >= MIN_A and A <= MAX_A, "Wrong A"
    assert fee <= MAX_FEE, "Fee too high"
    assert fee >= MIN_FEE, "Fee too low"
    assert admin_fee < MAX_ADMIN_FEE, "Admin fee too high"
    assert liquidation_discount >= MIN_LIQUIDATION_DISCOUNT, "Liquidation discount too low"
    assert loan_discount <= MAX_LOAN_DISCOUNT, "Loan discount too high"
    assert loan_discount > liquidation_discount, "need loan_discount>liquidation_discount"
    assert mp_idx < self.n_monetary_policies, "Invalid monetary policy index"

    p: uint256 = PriceOracle(_price_oracle_contract).price()  # This also validates price oracle ABI
    assert p > 0
    assert PriceOracle(_price_oracle_contract).price_w() == p

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
        _price_oracle_contract,
        code_offset=3
    )
    # `AMM` is deployed in constructor of `MarketOperator`
    amm: address = MarketOperator(market).AMM()

    N: uint256 = self.n_collaterals
    self.collaterals[N] = token
    for i in range(1000):
        if self.collaterals_index[token][i] == 0:
            self.collaterals_index[token][i] = 2**128 + N
            break
        assert i != 999, "Too many markets for same collateral"
    self.markets[N] = market
    self.amms[N] = amm
    self.n_collaterals = N + 1

    self.market_contracts[market] = MarketContracts({collateral: token, amm: amm, mp_idx: mp_idx})

    # log AddMarket(token, market, amm, mp_idx, N)
    return [market, amm]


@external
@view
def get_market(collateral: address, i: uint256 = 0) -> address:
    """
    @notice Get market address for collateral
    @param collateral Address of collateral token
    @param i Iterate over several markets for collateral if needed
    """
    return self.markets[self.collaterals_index[collateral][i] - 2**128]


@external
@view
def get_amm(collateral: address, i: uint256 = 0) -> address:
    """
    @notice Get AMM address for collateral
    @param collateral Address of collateral token
    @param i Iterate over several amms for collateral if needed
    """
    return self.amms[self.collaterals_index[collateral][i] - 2**128]


@view
@external
def peg_keeper_debt() -> uint256:
    regulator: PegKeeperRegulator = self.peg_keeper_regulator
    if regulator.address == empty(address):
        return 0
    return regulator.total_debt()


@external
@nonreentrant('lock')
def set_implementations(market: address, amm: address):
    """
    @notice Set new implementations (blueprints) for market and amm. Doesn't change existing ones
    @param market Address of the market blueprint
    @param amm Address of the AMM blueprint
    """
    assert msg.sender == CORE_OWNER.owner()
    assert market != empty(address)
    assert amm != empty(address)
    self.market_operator_implementation = market
    self.amm_implementation = amm
    log SetImplementations(amm, market)


@external
def set_market_hooks(market: address, hooks: address, hooks_bitfield: uint256):
    """
    @param hooks_bitfield Bitfield indicating which hook IDs are active. The bit offset
                          is equal to the values in the HookId enum, counting from 0.
                          For example, a bitfield of 0b0101 indicates that ON_ADJUST_LOAN
                          and ON_LIQUIDATION hooks are active.
    """
    assert msg.sender == CORE_OWNER.owner()
    assert hooks_bitfield >> NUM_HOOK_IDS == 0

    hookdata: uint256 = (convert(hooks, uint256) << 96) + hooks_bitfield
    if market == empty(address):
        self.global_hooks = hookdata
    else:
        self.market_hooks[market] = hookdata


@external
def set_amm_hook(market: address, hook: address):
    assert msg.sender == CORE_OWNER.owner()
    amm: address = self._get_contracts(market).amm
    AMM(amm).set_exchange_hook(hook)
    self.amm_hooks[amm] = hook


@external
def add_new_monetary_policy(monetary_policy: address):
    assert msg.sender == CORE_OWNER.owner()
    idx: uint256 = self.n_monetary_policies
    self.monetary_policies[idx] = monetary_policy
    self.n_monetary_policies = idx +1


@external
def change_existing_monetary_policy(monetary_policy: address, mp_idx: uint256):
    assert msg.sender == CORE_OWNER.owner()
    assert mp_idx < self.n_monetary_policies
    self.monetary_policies[mp_idx] = monetary_policy


@external
def change_market_monetary_policy(market: address, mp_idx: uint256):
    assert msg.sender == CORE_OWNER.owner()
    assert mp_idx < self.n_monetary_policies
    self.market_contracts[market].mp_idx = mp_idx


@external
def set_peg_keeper_regulator(regulator: PegKeeperRegulator, debt_ceiling: uint256):
    assert msg.sender == CORE_OWNER.owner()
    old: PegKeeperRegulator = self.peg_keeper_regulator
    if old.address != empty(address):
        old.recall_debt(self.peg_keeper_debt_ceiling)
    if regulator.address != empty(address):
        assert regulator.max_debt() + regulator.owed_debt() == 0
        regulator.recall_debt(0)
        STABLECOIN.mint(regulator.address, debt_ceiling)
    self.peg_keeper_regulator = regulator
    self.peg_keeper_debt_ceiling = debt_ceiling


@external
def set_peg_keeper_debt_ceiling(debt_ceiling: uint256):
    assert msg.sender == CORE_OWNER.owner()
    regulator: PegKeeperRegulator = self.peg_keeper_regulator
    current: uint256 = self.peg_keeper_debt_ceiling
    if debt_ceiling < current:
        regulator.recall_debt(current - debt_ceiling)
    else:
        STABLECOIN.mint(regulator.address, debt_ceiling - current)

    self.peg_keeper_debt_ceiling = debt_ceiling


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
    if (hookdata >> (convert(hook_id, uint256) - 1)) & 1 == 0:
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


@external
@nonreentrant('lock')
def create_loan(account: address, market: address, coll_amount: uint256, debt_amount: uint256, n_bands: uint256):
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

    self.total_debt += debt_increase
    self.minted += debt_amount

    STABLECOIN.mint(msg.sender, debt_amount)

    log CreateLoan(market, account, coll_amount, debt_amount_final)


@external
@nonreentrant('lock')
def adjust_loan(account: address, market: address, coll_change: int256, debt_change: int256, max_active_band: int256 = 2**255-1):
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

    self.total_debt = self._uint_plus_int(self.total_debt, debt_adjustment)

    if debt_change != 0:
        debt_change_abs: uint256 = convert(abs(debt_change), uint256)
        if debt_change > 0:
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
    for i in range(255):
        if i == len(market_list):
            break

        market: address = market_list[i]
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


@external
@view
def stored_admin_fees() -> uint256:
    """
    @notice Calculate the amount of fees obtained from the interest
    """
    return self.total_debt + self.redeemed - self.minted
