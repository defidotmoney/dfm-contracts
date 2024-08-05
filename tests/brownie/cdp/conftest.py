import pytest
from brownie_tokens import ERC20


@pytest.fixture(scope="module")
def oracle(dummy_oracle):
    # for CDP tests we rename `dummy_oracle` to `oracle`
    return dummy_oracle


@pytest.fixture(scope="module")
def policy2(ConstantMonetaryPolicy, deployer):
    return ConstantMonetaryPolicy.deploy({"from": deployer})


@pytest.fixture(scope="module")
def regulator(PegKeeperRegulator, core, stable, agg_stable, controller, deployer):
    contract = PegKeeperRegulator.deploy(
        core, controller, stable, agg_stable, 3 * 10**14, 5 * 10**14, 0, {"from": deployer}
    )
    stable.setMinter(contract, True, {"from": deployer})
    controller.set_peg_keeper_regulator(contract, False, {"from": deployer})

    return contract


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
def many_hooks(ControllerHookTester, deployer):
    contracts = [ControllerHookTester.deploy({"from": deployer}) for i in range(4)]
    for c in contracts:
        c.set_configuration(0, [True, True, True, True], {"from": deployer})
    return contracts
