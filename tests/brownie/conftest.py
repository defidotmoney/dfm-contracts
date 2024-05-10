import pytest
from brownie_tokens import ERC20


PEGKEEPER_CAP = 10_000_000 * 10**18
PK_COUNT = 3

MARKET_DEBT_CAP = 10_000_000 * 10**18

MARKET_A = 100
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
def mock_endpoint(MockEndpoint, deployer):
    return MockEndpoint.deploy({"from": deployer})


@pytest.fixture(scope="module")
def stable(StableCoin, core, deployer, mock_endpoint):
    return StableCoin.deploy(core, "Test Stablecoin", "TST", mock_endpoint, {"from": deployer})


@pytest.fixture(scope="module")
def policy(ConstantMonetaryPolicy, deployer):
    return ConstantMonetaryPolicy.deploy({"from": deployer})


@pytest.fixture(scope="module")
def policy2(ConstantMonetaryPolicy, deployer):
    return ConstantMonetaryPolicy.deploy({"from": deployer})


@pytest.fixture(scope="module")
def oracle(DummyPriceOracle, deployer):
    return DummyPriceOracle.deploy(3000 * 10**18, {"from": deployer})


@pytest.fixture(scope="module")
def agg_stable(AggregateStablePrice2, core, stable, deployer):
    return AggregateStablePrice2.deploy(core, stable, 10**15, {"from": deployer})


@pytest.fixture(scope="module")
def controller(MainController, MarketOperator, AMM, core, stable, policy, deployer):
    contract = MainController.deploy(core, stable, [policy], 2**256 - 1, {"from": deployer})
    stable.setMinter(contract, True, {"from": deployer})

    market_impl = MarketOperator.deploy(core, contract, stable, MARKET_A, {"from": deployer})
    amm_impl = AMM.deploy(contract, stable, MARKET_A, {"from": deployer})
    contract.set_implementations(MARKET_A, market_impl, amm_impl, {"from": deployer})

    return contract


@pytest.fixture(scope="module")
def regulator(PegKeeperRegulator, core, stable, agg_stable, controller, deployer):
    contract = PegKeeperRegulator.deploy(core, stable, agg_stable, controller, {"from": deployer})
    stable.setMinter(contract, True, {"from": deployer})
    controller.set_peg_keeper_regulator(contract, False, {"from": deployer})

    return contract


@pytest.fixture(scope="module")
def pk_swapcoins():
    return [ERC20() for i in range(PK_COUNT)]


@pytest.fixture(scope="module")
def pk_swaps(Stableswap, pk_swapcoins, stable, deployer, agg_stable):
    swap_list = []
    for i in range(PK_COUNT):
        coin = pk_swapcoins[i]
        rate_mul = [10 ** (36 - coin.decimals()), 10 ** (36 - stable.decimals())]
        swap = Stableswap.deploy(
            f"PegPool {i+1}", f"PP{i+1}", [coin, stable], rate_mul, 50, 1000000, {"from": deployer}
        )
        agg_stable.add_price_pair(swap, {"from": deployer})
        swap_list.append(swap)
    return swap_list


@pytest.fixture(scope="module")
def peg_keepers(PegKeeper, pk_swaps, core, stable, deployer, regulator, controller):
    pk_list = []
    for swap in pk_swaps:
        peg_keeper = PegKeeper.deploy(
            core, regulator, controller, stable, swap, 2 * 10**4, {"from": deployer}
        )
        # regulator.add_peg_keeper(peg_keeper, PEGKEEPER_CAP, {"from": deployer})
        pk_list.append(peg_keeper)

    return pk_list


@pytest.fixture(scope="module")
def pk(peg_keepers):
    return peg_keepers[0]


@pytest.fixture(scope="module")
def collateral():
    return ERC20(success=True, fail="revert")


@pytest.fixture(scope="module")
def collateral2():
    return ERC20(success=None, fail="revert")


@pytest.fixture(scope="module")
def collateral3():
    return ERC20(success=True, fail=False)


@pytest.fixture(scope="module")
def collateral_list(collateral, collateral2, collateral3):
    return [collateral, collateral2, collateral3]


@pytest.fixture(scope="module")
def _deploy_market(MarketOperator, controller, oracle, deployer):
    def fn(collateral):
        controller.add_market(
            collateral,
            MARKET_A,
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

    return fn


@pytest.fixture(scope="module")
def market(_deploy_market, collateral):
    return _deploy_market(collateral)


@pytest.fixture(scope="module")
def market2(_deploy_market, collateral2):
    return _deploy_market(collateral2)


@pytest.fixture(scope="module")
def market3(_deploy_market, collateral3):
    return _deploy_market(collateral3)


@pytest.fixture(scope="module")
def market_list(market, market2, market3):
    return [market, market2, market3]


@pytest.fixture(scope="module")
def amm(AMM, controller, market):
    return AMM.at(controller.market_contracts(market)["amm"])


@pytest.fixture(scope="module")
def amm2(AMM, controller, market2):
    return AMM.at(controller.market_contracts(market2)["amm"])


@pytest.fixture(scope="module")
def amm3(AMM, controller, market3):
    return AMM.at(controller.market_contracts(market3)["amm"])


@pytest.fixture(scope="module")
def amm_list(amm, amm2, amm3):
    return [amm, amm2, amm3]


@pytest.fixture(scope="module")
def hooks(ControllerHookTester, deployer):
    return ControllerHookTester.deploy({"from": deployer})


@pytest.fixture(scope="module")
def amm_hook(AmmHookTester, controller, collateral, amm, deployer):
    return AmmHookTester.deploy(controller, collateral, amm, {"from": deployer})
