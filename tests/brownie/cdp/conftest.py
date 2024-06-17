import pytest
from brownie_tokens import ERC20

PK_COUNT = 3


@pytest.fixture(scope="module")
def oracle(dummy_oracle):
    # for CDP tests we rename `dummy_oracle` to `oracle`
    return dummy_oracle


@pytest.fixture(scope="module")
def policy2(ConstantMonetaryPolicy, deployer):
    return ConstantMonetaryPolicy.deploy({"from": deployer})


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
        pk_list.append(peg_keeper)

    return pk_list


@pytest.fixture(scope="module")
def pk(peg_keepers):
    return peg_keepers[0]


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
