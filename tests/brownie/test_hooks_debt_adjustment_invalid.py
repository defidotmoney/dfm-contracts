import pytest

import brownie
from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(hooks, collateral, controller, market, stable, alice, deployer):
    for acct in [deployer, alice]:
        collateral._mint_for_testing(acct, 100 * 10**18)
        collateral.approve(controller, 2**256 - 1, {"from": acct})

    controller.set_market_hooks(ZERO_ADDRESS, hooks, [True, True, True, True], {"from": deployer})

    # ensure initial hook debt is sufficient for negative adjustments
    stable.mint(deployer, 1000 * 10**18, {"from": controller})
    controller.increase_total_hook_debt_adjustment(market, 1000 * 10**18, {"from": deployer})


def test_create_loan_adjust(market, controller, alice, hooks):
    amount = 1000 * 10**18
    hooks.set_response(-amount - 1, {"from": alice})
    with brownie.reverts("DFM:C Hook caused invalid debt"):
        controller.create_loan(alice, market, 50 * 10**18, amount, 5, {"from": alice})

    hooks.set_response(-amount, {"from": alice})
    with brownie.reverts("DFM:M No loan"):
        controller.create_loan(alice, market, 50 * 10**18, amount, 5, {"from": alice})


def test_adjust_loan_increase_debt(market, hooks, controller, alice):
    amount = 1000 * 10**18
    controller.create_loan(alice, market, 50 * 10**18, amount, 5, {"from": alice})

    hooks.set_response(-amount - 1, {"from": alice})
    with brownie.reverts("DFM:C Hook caused invalid debt"):
        controller.adjust_loan(alice, market, 0, amount, {"from": alice})

    hooks.set_response(-amount, {"from": alice})
    controller.adjust_loan(alice, market, 0, amount, {"from": alice})


def test_adjust_loan_decrease_debt(market, hooks, controller, alice):
    amount = 1000 * 10**18
    controller.create_loan(alice, market, 50 * 10**18, amount, 5, {"from": alice})

    hooks.set_response(amount + 1, {"from": alice})
    with brownie.reverts("DFM:C Hook caused invalid debt"):
        controller.adjust_loan(alice, market, 0, -amount, {"from": alice})

    hooks.set_response(amount, {"from": alice})
    controller.adjust_loan(alice, market, 0, -amount, {"from": alice})


def test_adjust_loan_debt_unchanged(market, hooks, controller, alice):
    amount = 1000 * 10**18
    controller.create_loan(alice, market, 50 * 10**18, amount, 5, {"from": alice})

    hooks.set_response(1, {"from": alice})
    with brownie.reverts("DFM:C Hook caused invalid debt"):
        controller.adjust_loan(alice, market, 5 * 10**18, 0, {"from": alice})

    hooks.set_response(-1, {"from": alice})
    with brownie.reverts("DFM:C Hook caused invalid debt"):
        controller.adjust_loan(alice, market, 5 * 10**18, 0, {"from": alice})

    hooks.set_response(0, {"from": alice})
    controller.adjust_loan(alice, market, 5 * 10**18, 0, {"from": alice})


def test_close_loan(market, hooks, controller, alice):
    amount = 1000 * 10**18
    controller.create_loan(alice, market, 50 * 10**18, amount, 5, {"from": alice})

    hooks.set_response(-amount - 1, {"from": alice})
    with brownie.reverts("DFM:C Hook caused invalid debt"):
        controller.close_loan(alice, market, {"from": alice})

    hooks.set_response(-amount, {"from": alice})
    controller.close_loan(alice, market, {"from": alice})


def test_liquidate(market, hooks, controller, oracle, alice):
    amount = 1000 * 10**18
    controller.create_loan(alice, market, 50 * 10**18, amount, 5, {"from": alice})
    oracle.set_price(2100 * 10**18, {"from": alice})

    hooks.set_response(-amount - 1, {"from": alice})
    with brownie.reverts("DFM:C Hook caused invalid debt"):
        controller.liquidate(market, alice, 0, {"from": alice})

    hooks.set_response(-amount, {"from": alice})
    controller.liquidate(market, alice, 0, {"from": alice})
