import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, alice, controller):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})


def test_create_loan(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    assert stable.totalSupply() == 1000 * 10**18
    assert stable.balanceOf(alice) == 1000 * 10**18

    assert collateral.balanceOf(alice) == 50 * 10**18
    assert collateral.balanceOf(amm) == 50 * 10**18

    assert market.user_state(alice)[:3] == (50 * 10**18, 0, 1000 * 10**18)


def test_add_collateral(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, 25 * 10**18, 0, {"from": alice})

    assert stable.totalSupply() == 1000 * 10**18
    assert stable.balanceOf(alice) == 1000 * 10**18

    assert collateral.balanceOf(alice) == 25 * 10**18
    assert collateral.balanceOf(amm) == 75 * 10**18

    assert market.user_state(alice)[:3] == (75 * 10**18, 0, 1000 * 10**18)


def test_remove_collateral(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, -10 * 10**18, 0, {"from": alice})

    assert stable.totalSupply() == 1000 * 10**18
    assert stable.balanceOf(alice) == 1000 * 10**18

    assert collateral.balanceOf(alice) == 60 * 10**18
    assert collateral.balanceOf(amm) == 40 * 10**18

    assert market.user_state(alice)[:3] == (40 * 10**18, 0, 1000 * 10**18)


def test_borrow_more(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, 20 * 10**18, 500 * 10**18, {"from": alice})

    assert stable.totalSupply() == 1500 * 10**18
    assert stable.balanceOf(alice) == 1500 * 10**18

    assert collateral.balanceOf(alice) == 30 * 10**18
    assert collateral.balanceOf(amm) == 70 * 10**18

    assert market.user_state(alice)[:3] == (70 * 10**18, 0, 1500 * 10**18)


def test_repay(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.close_loan(alice, market, {"from": alice})

    assert stable.totalSupply() == 0

    assert collateral.balanceOf(alice) == 100 * 10**18
    assert collateral.balanceOf(amm) == 0

    assert market.user_state(alice)[:3] == (0, 0, 0)


def test_repay_partial(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, 0, -600 * 10**18, {"from": alice})

    assert stable.totalSupply() == 400 * 10**18
    assert stable.balanceOf(alice) == 400 * 10**18

    assert collateral.balanceOf(alice) == 50 * 10**18
    assert collateral.balanceOf(amm) == 50 * 10**18

    assert market.user_state(alice)[:3] == (50 * 10**18, 0, 400 * 10**18)
