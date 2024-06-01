import pytest

from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(hooks, collateral, controller, alice):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})


def _hook_assertions(tx, is_enabled):
    if is_enabled:
        assert "HookFired" in tx.events
    else:
        assert "HookFired" not in tx.events


@pytest.mark.parametrize("is_global", [True, False])
@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_active_create_loan(market, controller, alice, deployer, hooks, is_enabled, is_global):
    hooks.set_configuration(0, [is_enabled, False, False, True], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS if is_global else market, hooks, {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, is_enabled)


@pytest.mark.parametrize("is_global", [True, False])
@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_active_adjust_loan(market, hooks, controller, alice, deployer, is_enabled, is_global):
    hooks.set_configuration(0, [False, is_enabled, False, True], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS if is_global else market, hooks, {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, False)

    tx = controller.adjust_loan(alice, market, 0, 1000 * 10**18, {"from": alice})
    _hook_assertions(tx, is_enabled)


@pytest.mark.parametrize("is_global", [True, False])
@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_active_close_loan(market, hooks, controller, alice, deployer, is_enabled, is_global):
    hooks.set_configuration(0, [False, False, is_enabled, True], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS if is_global else market, hooks, {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, False)

    tx = controller.close_loan(alice, market, {"from": alice})
    _hook_assertions(tx, is_enabled)


@pytest.mark.parametrize("is_global", [True, False])
@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_active_liq(market, hooks, controller, oracle, alice, deployer, is_enabled, is_global):
    hooks.set_configuration(0, [False, False, True, is_enabled], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS if is_global else market, hooks, {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, False)

    oracle.set_price(2000 * 10**18, {"from": alice})
    tx = controller.liquidate(market, alice, 0, {"from": alice})
    _hook_assertions(tx, is_enabled)
