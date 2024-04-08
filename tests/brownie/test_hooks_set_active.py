import pytest

import brownie
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


@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_hook_active_create_loan(market, controller, alice, deployer, hooks, is_enabled):
    controller.set_market_hooks(ZERO_ADDRESS, hooks, [is_enabled, 0, 0, 0], {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, is_enabled)


@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_hook_active_adjust_loan(market, hooks, controller, alice, deployer, is_enabled):
    controller.set_market_hooks(ZERO_ADDRESS, hooks, [0, is_enabled, 0, 0], {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, False)

    tx = controller.adjust_loan(alice, market, 0, 1000 * 10**18, {"from": alice})
    _hook_assertions(tx, is_enabled)


@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_hook_active_close_loan(market, hooks, controller, alice, deployer, is_enabled):
    controller.set_market_hooks(ZERO_ADDRESS, hooks, [0, 0, is_enabled, 0], {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, False)

    tx = controller.close_loan(alice, market, {"from": alice})
    _hook_assertions(tx, is_enabled)


@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_hook_active_liquidate(market, hooks, controller, oracle, alice, deployer, is_enabled):
    controller.set_market_hooks(ZERO_ADDRESS, hooks, [0, 0, 0, is_enabled], {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, False)

    oracle.set_price(2000 * 10**18, {"from": alice})
    tx = controller.liquidate(market, alice, 0, {"from": alice})
    _hook_assertions(tx, is_enabled)
