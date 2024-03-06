import pytest

import brownie
from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(hooks, collateral, controller, alice, deployer):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})
    controller.set_market_hooks(ZERO_ADDRESS, hooks, 0b1111, {"from": deployer})


def test_create_loan(market, controller, alice, hooks):
    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    subcalls = [i for i in tx.subcalls if i["to"] == hooks]
    assert len(subcalls) == 1
    assert subcalls[0]["function"] == "on_create_loan(address,address,uint256,uint256)"


def test_create_loan_reverts(market, controller, alice, hooks):
    hooks.set_is_reverting(True, {"from": alice})

    with brownie.reverts("Hook is reverting"):
        controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})


def test_adjust_loan(market, hooks, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    tx = controller.adjust_loan(alice, market, 25 * 10**18, 0, {"from": alice})

    subcalls = [i for i in tx.subcalls if i["to"] == hooks]
    assert len(subcalls) == 1
    assert subcalls[0]["function"] == "on_adjust_loan(address,address,int256,int256)"


def test_adjust_loan_reverts(market, hooks, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_is_reverting(True, {"from": alice})
    with brownie.reverts("Hook is reverting"):
        controller.adjust_loan(alice, market, 25 * 10**18, 0, {"from": alice})


def test_close_loan(market, hooks, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    tx = controller.close_loan(alice, market, {"from": alice})

    subcalls = [i for i in tx.subcalls if i["to"] == hooks]
    assert len(subcalls) == 1
    assert subcalls[0]["function"] == "on_close_loan(address,address,uint256)"


def test_close_loan_reverts(market, hooks, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_is_reverting(True, {"from": alice})
    with brownie.reverts("Hook is reverting"):
        controller.close_loan(alice, market, {"from": alice})


# TODO test liquidations
