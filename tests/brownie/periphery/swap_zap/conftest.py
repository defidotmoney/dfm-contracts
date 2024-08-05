import pytest


@pytest.fixture(scope="module")
def router(RouterMock, controller, stable, collateral_list, deployer):
    contract = RouterMock.deploy({"from": deployer})

    for token in collateral_list:
        token._mint_for_testing(contract, 10**25, {"from": deployer})

    stable.mint(contract, 10**25, {"from": controller})
    deployer.transfer(contract, "100 ether")

    return contract


@pytest.fixture(scope="module")
def zap(SwapZap, controller, stable, router, deployer):
    return SwapZap.deploy(controller, stable, router, {"from": deployer})
