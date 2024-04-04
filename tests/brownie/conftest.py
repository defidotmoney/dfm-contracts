import pytest
from brownie import ZERO_ADDRESS, compile_source
from brownie_tokens import ERC20


from scripts.deploy_blueprint import deploy_blueprint


PEGKEEPER_CAP = 10_000_000 * 10**18
PK_COUNT = 3

MARKET_DEBT_CAP = 10_000_000 * 10**18

market_A = 100
market_fee = 6 * 10**15  # 0.6%
market_admin_fee = 5 * 10**17  # 50% of the market fee
market_loan_discount = 9 * 10**16  # 9%; +2% from 4x 1% bands = 100% - 11% = 89% LTV
market_liquidation_discount = 6 * 10**16  # 6%


@pytest.fixture(scope="function", autouse=True)
def base_setup(fn_isolation):
    pass


@pytest.fixture(scope="module")
def deployer(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def alice(accounts):
    return accounts[1]


@pytest.fixture(scope="module")
def bob(accounts):
    return accounts[2]


@pytest.fixture(scope="module")
def fee_receiver():
    return "000000000000000000000000000000000000fee5"


@pytest.fixture(scope="module")
def core(CoreOwner, deployer, fee_receiver):
    return CoreOwner.deploy(fee_receiver, {"from": deployer})


@pytest.fixture(scope="module")
def stable(StableCoin, deployer):
    return StableCoin.deploy({"from": deployer})


@pytest.fixture(scope="module")
def policy(ConstantMonetaryPolicy, deployer):
    return ConstantMonetaryPolicy.deploy({"from": deployer})


@pytest.fixture(scope="module")
def oracle(DummyPriceOracle, deployer):
    return DummyPriceOracle.deploy(3000 * 10**18, {"from": deployer})


@pytest.fixture(scope="module")
def agg_stable(AggregateStablePrice2, core, stable, deployer):
    return AggregateStablePrice2.deploy(core, stable, 10**15, {"from": deployer})


@pytest.fixture(scope="module")
def controller(MainController, MarketOperator, AMM, core, stable, policy, deployer):
    market_impl = deploy_blueprint(MarketOperator, deployer)
    amm_impl = deploy_blueprint(AMM, deployer)
    contract = MainController.deploy(
        core, stable, market_impl, amm_impl, [policy], {"from": deployer}
    )
    stable.setMinter(contract, True, {"from": deployer})
    return contract


@pytest.fixture(scope="module")
def regulator(PegKeeperRegulator, core, stable, agg_stable, controller, deployer):
    contract = PegKeeperRegulator.deploy(core, stable, agg_stable, controller, {"from": deployer})
    controller.set_peg_keeper_regulator(contract, PEGKEEPER_CAP * PK_COUNT, {"from": deployer})

    return contract


@pytest.fixture(scope="module")
def peg_keepers(PegKeeper, Stableswap, core, stable, deployer, regulator, agg_stable):
    pk_list = []
    for i in range(1, PK_COUNT + 1):
        coin = ERC20()
        rate_mul = [10 ** (36 - coin.decimals()), 10 ** (36 - stable.decimals())]
        swap = Stableswap.deploy(
            f"PegPool {i}", f"PP{i}", [coin, stable], rate_mul, 500, 1000000, {"from": deployer}
        )
        agg_stable.add_price_pair(swap, {"from": deployer})
        peg_keeper = PegKeeper.deploy(core, swap, 2 * 10**4, regulator, {"from": deployer})
        regulator.add_peg_keeper(peg_keeper, PEGKEEPER_CAP, {"from": deployer})
        pk_list.append(peg_keeper)

    return pk_list


@pytest.fixture(scope="module")
def collateral():
    return ERC20()


@pytest.fixture(scope="module")
def market(MarketOperator, controller, collateral, oracle, deployer):
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
        {"from": deployer},
    )
    return MarketOperator.at(controller.get_market(collateral))


@pytest.fixture(scope="module")
def amm(AMM, controller, market):
    return AMM.at(controller.market_contracts(market)["amm"])


@pytest.fixture(scope="module")
def hooks(ControllerHookTester, deployer):
    return ControllerHookTester.deploy({"from": deployer})


@pytest.fixture(scope="module")
def amm_hook(AmmHookTester, collateral, amm, deployer):
    return AmmHookTester.deploy(collateral, amm, {"from": deployer})
