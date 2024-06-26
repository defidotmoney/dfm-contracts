import pytest

import brownie
from brownie import ZERO_ADDRESS

# test that hook reverts properly bubble up


@pytest.fixture(scope="module", autouse=True)
def setup(hooks, collateral, controller, alice, deployer):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})

    hooks.set_is_reverting(True, {"from": alice})


def test_set_hook_active_create_loan(market, controller, hooks, alice, deployer):
    hooks.set_configuration(0, [True, True, True, True], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})
    with brownie.reverts("Hook is reverting"):
        controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})


def test_set_hook_active_adjust_loan(market, hooks, controller, alice, deployer):
    hooks.set_configuration(0, [False, True, False, False], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})

    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    with brownie.reverts("Hook is reverting"):
        controller.adjust_loan(alice, market, 0, 1000 * 10**18, {"from": alice})


def test_set_hook_active_close_loan(market, hooks, controller, alice, deployer):
    hooks.set_configuration(0, [False, False, True, False], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})

    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    with brownie.reverts("Hook is reverting"):
        controller.close_loan(alice, market, {"from": alice})


def test_set_hook_active_liquidate(market, hooks, controller, alice, deployer):
    hooks.set_configuration(0, [False, False, False, True], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})

    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})

    with brownie.reverts("Hook is reverting"):
        controller.liquidate(market, alice, 0, {"from": alice})
