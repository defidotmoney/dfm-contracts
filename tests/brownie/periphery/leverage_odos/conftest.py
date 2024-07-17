import pytest


@pytest.fixture(scope="module")
def router(RouterMock, controller, stable, collateral, deployer):
    contract = RouterMock.deploy({"from": deployer})
    collateral._mint_for_testing(contract, 10**25, {"from": deployer})
    stable.mint(contract, 10**25, {"from": controller})
    return contract


@pytest.fixture(scope="module")
def zap(LeverageZapOdosV2, controller, stable, router, deployer):
    return LeverageZapOdosV2.deploy(controller, stable, router, {"from": deployer})
