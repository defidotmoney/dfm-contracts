from brownie import accounts
from brownie import (
    AggregateStablePrice,
    AMM,
    BridgeToken,
    DFMProtocolCore,
    MainController,
    MarketOperator,
    PegKeeper,
    PegKeeperRegulator,
)
from brownie import ConstantMonetaryPolicy, DummyPriceOracle, MockLzEndpoint, Stableswap
from brownie_tokens import ERC20
from scripts.utils.rate0 import apy_to_rate0


# deployment constants, these can be modified to suit your needs

GLOBAL_DEBT_CAP = 100_000_000 * 10**18
MARKET_DEBT_CAP = 10_000_000 * 10**18
PEGKEEPER_CAP = 1_000_000 * 10**18
FEE_RECEIVER = "000000000000000000000000000000000000fee5"

MARKET_A = 100
MARKET_FEE = 6 * 10**15  # 0.6%
MARKET_ADMIN_FEE = 0
MARKET_LOAN_DISCOUNT = 9 * 10**16  # 9%; +2% from 4x 1% bands = 100% - 11% = 89% LTV
MARKET_LIQUIDATION_FEE = 6 * 10**16  # 6%
MARKET_INTEREST_RATE = 0.1  # 10% APY


def main(acct=None, peg_keeper_count=3, market_count=3):
    """
    Deploys core Defi.Money contracts onto a local test network such as hardhat.
    """
    if acct is None:
        acct = accounts[0]

    # Deploy dummy/mock contracts
    endpoint = MockLzEndpoint.deploy({"from": acct})
    oracle = DummyPriceOracle.deploy(3000 * 10**18, {"from": acct})
    policy = ConstantMonetaryPolicy.deploy({"from": acct})
    policy.set_rate(apy_to_rate0(MARKET_INTEREST_RATE), {"from": acct})

    # Deploy core protocol contracts
    core = DFMProtocolCore.deploy(acct, FEE_RECEIVER, 0, {"from": acct})
    stable = BridgeToken.deploy(core, "Stablecoin", "STABLE", endpoint, b"", [], {"from": acct})
    controller = MainController.deploy(core, stable, [policy], GLOBAL_DEBT_CAP, {"from": acct})
    market_impl = MarketOperator.deploy(core, controller, MARKET_A, {"from": acct})
    amm_impl = AMM.deploy(controller, stable, MARKET_A, {"from": acct})

    # Setup and configure core contracts
    controller.set_implementations(MARKET_A, market_impl, amm_impl, {"from": acct})
    stable.setMinter(controller, True, {"from": acct})

    # OPTIONAL: deploy peg keepers with test AMMs
    # Not required in local deploy as `ConstantMonetaryPolicy` need `AggregateStablePrice`
    if peg_keeper_count:
        agg_stable = AggregateStablePrice.deploy(core, stable, 10**15, {"from": acct})
        regulator = PegKeeperRegulator.deploy(
            core, controller, stable, agg_stable, 10**15, 100, 0, {"from": acct}
        )

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

    # Deploy test collaterals and creat markets for them
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
