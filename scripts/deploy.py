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
    Stableswap,
    StableCoin,
    CoreOwner,
)
from brownie_tokens import ERC20
from scripts.rate0 import apr_to_rate0


GLOBAL_DEBT_CAP = 100_000_000 * 10**18
MARKET_DEBT_CAP = 10_000_000 * 10**18
PEGKEEPER_CAP = 1_000_000 * 10**18
FEE_RECEIVER = "000000000000000000000000000000000000fee5"


MARKET_A = 100
MARKET_FEE = 6 * 10**15  # 0.6%
MARKET_ADMIN_FEE = 0
MARKET_LOAN_DISCOUNT = 9 * 10**16  # 9%; +2% from 4x 1% bands = 100% - 11% = 89% LTV
MARKET_LIQUIDATION_FEE = 6 * 10**16  # 6%
MARKET_INTEREST_RATE = 0.1  # 10% APR


def deploy_local(acct=None, peg_keeper_count=3, market_count=3):
    if acct is None:
        acct = accounts[0]

    # deploy dummy/mock contracts
    oracle = DummyPriceOracle.deploy(3000 * 10**18, {"from": acct})
    policy = ConstantMonetaryPolicy.deploy({"from": acct})
    policy.set_rate(apr_to_rate0(MARKET_INTEREST_RATE), {"from": acct})

    # deploy core protocol
    core = CoreOwner.deploy(FEE_RECEIVER, {"from": acct})
    stable = StableCoin.deploy({"from": acct})
    controller = MainController.deploy(core, stable, [policy], GLOBAL_DEBT_CAP, {"from": acct})
    market_impl = MarketOperator.deploy(core, controller, stable, MARKET_A, {"from": acct})
    amm_impl = AMM.deploy(controller, stable, MARKET_A, {"from": acct})

    # setup and config of core contracts
    controller.set_implementations(MARKET_A, market_impl, amm_impl, {"from": acct})
    stable.setMinter(controller, True, {"from": acct})

    # optional: deploy peg keepers with test AMMs
    if peg_keeper_count:
        agg_stable = AggregateStablePrice2.deploy(core, stable, 10**15, {"from": acct})
        regulator = PegKeeperRegulator.deploy(core, stable, agg_stable, controller, {"from": acct})

        controller.set_peg_keeper_regulator(regulator, False, {"from": acct})
        stable.setMinter(regulator, True, {"from": acct})

        for i in range(1, peg_keeper_count + 1):
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

    # deploy markets
    for i in range(1, market_count + 1):
        collateral = ERC20(f"Test Token {i}", f"TST{i}", deployer=acct)
        controller.add_market(
            collateral,
            MARKET_A,
            MARKET_FEE,
            MARKET_ADMIN_FEE,
            oracle,
            0,
            MARKET_LOAN_DISCOUNT,
            MARKET_LIQUIDATION_FEE,
            MARKET_DEBT_CAP,
            {"from": acct},
        )

    return controller
