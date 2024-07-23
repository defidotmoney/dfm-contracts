import pytest


@pytest.fixture(scope="module")
def compose_fwd(LzComposeForwarder, core, controller, stable, alice, bob, deployer):
    stable.setPeer(42, stable.address, {"from": deployer})
    stable.setPeer(31337, stable.address, {"from": deployer})

    c = LzComposeForwarder.deploy(core, stable, alice, bob, 31337, 80000, 1, {"from": deployer})
    stable.mint(c, 10**24, {"from": controller})

    return c
