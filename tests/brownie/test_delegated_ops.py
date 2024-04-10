import brownie
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, alice, bob, controller):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})

    controller.setDelegateApproval(alice, True, {"from": bob})


def test_create_loan(market, amm, collateral, stable, controller, alice, bob):
    controller.create_loan(bob, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    assert stable.totalSupply() == 1000 * 10**18
    assert stable.balanceOf(alice) == 1000 * 10**18

    assert collateral.balanceOf(alice) == 50 * 10**18
    assert collateral.balanceOf(amm) == 50 * 10**18

    assert market.user_state(bob)[:3] == (50 * 10**18, 0, 1000 * 10**18)
    assert market.user_state(alice)[:3] == (0, 0, 0)


def test_add_collateral(market, amm, collateral, stable, controller, alice, bob):
    controller.create_loan(bob, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(bob, market, 25 * 10**18, 0, {"from": alice})

    assert stable.totalSupply() == 1000 * 10**18
    assert stable.balanceOf(alice) == 1000 * 10**18

    assert collateral.balanceOf(alice) == 25 * 10**18
    assert collateral.balanceOf(amm) == 75 * 10**18

    assert market.user_state(bob)[:3] == (75 * 10**18, 0, 1000 * 10**18)
    assert market.user_state(alice)[:3] == (0, 0, 0)


def test_remove_collateral(market, amm, collateral, stable, controller, alice, bob):
    controller.create_loan(bob, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(bob, market, -10 * 10**18, 0, {"from": alice})

    assert stable.totalSupply() == 1000 * 10**18
    assert stable.balanceOf(alice) == 1000 * 10**18

    assert collateral.balanceOf(alice) == 60 * 10**18
    assert collateral.balanceOf(amm) == 40 * 10**18

    assert market.user_state(bob)[:3] == (40 * 10**18, 0, 1000 * 10**18)
    assert market.user_state(alice)[:3] == (0, 0, 0)


def test_borrow_more(market, amm, collateral, stable, controller, alice, bob):
    controller.create_loan(bob, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(bob, market, 20 * 10**18, 500 * 10**18, {"from": alice})

    assert stable.totalSupply() == 1500 * 10**18
    assert stable.balanceOf(alice) == 1500 * 10**18

    assert collateral.balanceOf(alice) == 30 * 10**18
    assert collateral.balanceOf(amm) == 70 * 10**18

    assert market.user_state(bob)[:3] == (70 * 10**18, 0, 1500 * 10**18)
    assert market.user_state(alice)[:3] == (0, 0, 0)


def test_repay(market, amm, collateral, stable, controller, alice, bob):
    controller.create_loan(bob, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.close_loan(bob, market, {"from": alice})

    assert stable.totalSupply() == 0

    assert collateral.balanceOf(alice) == 100 * 10**18
    assert collateral.balanceOf(amm) == 0

    assert market.user_state(alice)[:3] == (0, 0, 0)
    assert market.user_state(bob)[:3] == (0, 0, 0)


def test_repay_partial(market, amm, collateral, stable, controller, alice, bob):
    controller.create_loan(bob, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(bob, market, 0, -600 * 10**18, {"from": alice})

    assert stable.totalSupply() == 400 * 10**18
    assert stable.balanceOf(alice) == 400 * 10**18

    assert collateral.balanceOf(alice) == 50 * 10**18
    assert collateral.balanceOf(amm) == 50 * 10**18

    assert market.user_state(bob)[:3] == (50 * 10**18, 0, 400 * 10**18)
    assert market.user_state(alice)[:3] == (0, 0, 0)


def test_not_delegated(market, controller, alice, bob):
    with brownie.reverts("DFM:C Delegate not approved"):
        controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": bob})


def test_set_delegate_approval(market, controller, alice, bob):

    assert controller.isApprovedDelegate(bob, alice)
    controller.setDelegateApproval(alice, False, {"from": bob})

    assert not controller.isApprovedDelegate(bob, alice)

    with brownie.reverts("DFM:C Delegate not approved"):
        controller.create_loan(bob, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
