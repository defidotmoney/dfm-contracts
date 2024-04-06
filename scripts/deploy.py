from brownie import ZERO_ADDRESS, accounts
from brownie import (
    AggregateStablePrice2,
    ConstantMonetaryPolicy,
    DummyPriceOracle,
    AMM,
    MarketOperator,
    MainController,
    PegKeeper,
    PegKeeperRegulator,
)
from brownie import (
    Stableswap,
    StableCoin,
    CoreOwner,
)
from brownie_tokens import ERC20

from scripts.deploy_blueprint import deploy_blueprint


MARKET_DEBT_CAP = 10_000_000 * 10**18
PEGKEEPER_CAP = 1_000_000 * 10**18
FEE_RECEIVER = "000000000000000000000000000000000000fee5"


market_A = 100
market_fee = 6 * 10**15  # 0.6%
market_admin_fee = 0
market_loan_discount = 9 * 10**16  # 9%; +2% from 4x 1% bands = 100% - 11% = 89% LTV
market_liquidation_discount = 6 * 10**16  # 6%


def main(acct=None):
    if acct is None:
        acct = accounts[0]

    core = CoreOwner.deploy(FEE_RECEIVER, {"from": acct})
    stable = StableCoin.deploy({"from": acct})
    policy = ConstantMonetaryPolicy.deploy({"from": acct})
    oracle = DummyPriceOracle.deploy(3000 * 10**18, {"from": acct})
    agg_stable = AggregateStablePrice2.deploy(core, stable, 10**15, {"from": acct})
    market_impl = deploy_blueprint(MarketOperator, acct)
    amm_impl = deploy_blueprint(AMM, acct)

    controller = MainController.deploy(
        core, stable, market_impl, amm_impl, [policy], MARKET_DEBT_CAP, {"from": acct}
    )
    regulator = PegKeeperRegulator.deploy(core, stable, agg_stable, controller, {"from": acct})
    controller.set_peg_keeper_regulator(regulator, False, {"from": acct})

    stable.setMinter(controller, True, {"from": acct})
    stable.setMinter(regulator, True, {"from": acct})

    for i in range(1, 3):
        coin = ERC20()
        rate_mul = [10 ** (36 - coin.decimals()), 10 ** (36 - stable.decimals())]
        swap = Stableswap.deploy(
            f"PegPool {i}", f"PP{i}", [coin, stable], rate_mul, 500, 1000000, {"from": acct}
        )
        agg_stable.add_price_pair(swap, {"from": acct})
        peg_keeper = PegKeeper.deploy(
            core, regulator, controller, stable, swap, 2 * 10**4, {"from": acct}
        )
        regulator.add_peg_keeper(peg_keeper, PEGKEEPER_CAP, {"from": acct})

    collateral = ERC20()
    controller.add_market(
        collateral,
        market_A,
        market_fee,
        market_admin_fee,
        oracle,
        0,
        market_loan_discount,
        market_liquidation_discount,
        MARKET_DEBT_CAP,
        {"from": acct},
    )
    return controller, collateral
