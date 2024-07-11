import pytest

import brownie
from brownie import ZERO_ADDRESS


HOOK_ADJUSTMENT = 200 * 10**18


@pytest.fixture(scope="module", autouse=True)
def setup(hooks, collateral, controller, alice, deployer):
    for acct in [deployer, alice]:
        collateral._mint_for_testing(acct, 100 * 10**18)
        collateral.approve(controller, 2**256 - 1, {"from": acct})

    hooks.set_configuration(0, [True, True, True, True], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})


def test_create_loan(market, controller, alice, hooks):
    hooks.set_response(HOOK_ADJUSTMENT, {"from": alice})
    with brownie.reverts("DFM:C Hook cannot adjust debt"):
        controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_response(0, {"from": alice})
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})


def test_adjust_loan(market, hooks, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_response(HOOK_ADJUSTMENT, {"from": alice})
    with brownie.reverts("DFM:C Hook cannot adjust debt"):
        controller.adjust_loan(alice, market, 0, 1000 * 10**18, {"from": alice})

    hooks.set_response(0, {"from": alice})
    controller.adjust_loan(alice, market, 0, 1000 * 10**18, {"from": alice})


def test_close_loan(market, hooks, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_response(HOOK_ADJUSTMENT, {"from": alice})
    with brownie.reverts("DFM:C Hook cannot adjust debt"):
        controller.close_loan(alice, market, {"from": alice})

    hooks.set_response(0, {"from": alice})
    controller.close_loan(alice, market, {"from": alice})


def test_liquidation(market, controller, oracle, alice, hooks):
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    oracle.set_price(2100 * 10**18, {"from": alice})

    hooks.set_response(HOOK_ADJUSTMENT, {"from": alice})
    with brownie.reverts("DFM:C Hook cannot adjust debt"):
        controller.liquidate(market, alice, 0, {"from": alice})

    hooks.set_response(0, {"from": alice})
    controller.liquidate(market, alice, 0, {"from": alice})
