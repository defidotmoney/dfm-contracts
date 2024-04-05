import pytest

import brownie
from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, controller, alice):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})


def _hook_assertions(tx, is_enabled):
    if is_enabled:
        assert "HookFired" in tx.events
    else:
        assert "HookFired" not in tx.events


def test_invalid_hook_bitfield(controller, hooks, deployer):
    with brownie.reverts():
        controller.set_market_hooks(ZERO_ADDRESS, hooks, 0b10000, {"from": deployer})


@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_hook_active_create_loan(market, controller, alice, deployer, hooks, is_enabled):
    hooks_bitfield = 0b1 if is_enabled else 0
    controller.set_market_hooks(ZERO_ADDRESS, hooks, hooks_bitfield, {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, is_enabled)


@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_hook_active_adjust_loan(market, hooks, controller, alice, deployer, is_enabled):
    hooks_bitfield = 0b10 if is_enabled else 0
    controller.set_market_hooks(ZERO_ADDRESS, hooks, hooks_bitfield, {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, False)

    tx = controller.adjust_loan(alice, market, 0, 1000 * 10**18, {"from": alice})
    _hook_assertions(tx, is_enabled)


@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_hook_active_close_loan(market, hooks, controller, alice, deployer, is_enabled):
    hooks_bitfield = 0b100 if is_enabled else 0
    controller.set_market_hooks(ZERO_ADDRESS, hooks, hooks_bitfield, {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, False)

    tx = controller.close_loan(alice, market, {"from": alice})
    _hook_assertions(tx, is_enabled)


@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_hook_active_liquidate(market, hooks, controller, oracle, alice, deployer, is_enabled):
    hooks_bitfield = 0b1000 if is_enabled else 0
    controller.set_market_hooks(ZERO_ADDRESS, hooks, hooks_bitfield, {"from": deployer})

    tx = controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    _hook_assertions(tx, False)

    oracle.set_price(2000 * 10**18, {"from": alice})
    tx = controller.liquidate(market, alice, 0, {"from": alice})
    _hook_assertions(tx, is_enabled)
