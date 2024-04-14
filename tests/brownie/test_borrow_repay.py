import pytest
import brownie
from brownie import ZERO_ADDRESS


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
    assert market.total_debt() == 1000 * 10**18


def test_add_collateral(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, 25 * 10**18, 0, {"from": alice})

    assert stable.totalSupply() == 1000 * 10**18
    assert stable.balanceOf(alice) == 1000 * 10**18

    assert collateral.balanceOf(alice) == 25 * 10**18
    assert collateral.balanceOf(amm) == 75 * 10**18

    assert market.user_state(alice)[:3] == (75 * 10**18, 0, 1000 * 10**18)
    assert market.total_debt() == 1000 * 10**18


def test_remove_collateral(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, -10 * 10**18, 0, {"from": alice})

    assert stable.totalSupply() == 1000 * 10**18
    assert stable.balanceOf(alice) == 1000 * 10**18

    assert collateral.balanceOf(alice) == 60 * 10**18
    assert collateral.balanceOf(amm) == 40 * 10**18

    assert market.user_state(alice)[:3] == (40 * 10**18, 0, 1000 * 10**18)
    assert market.total_debt() == 1000 * 10**18


def test_borrow_more(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, 20 * 10**18, 500 * 10**18, {"from": alice})

    assert stable.totalSupply() == 1500 * 10**18
    assert stable.balanceOf(alice) == 1500 * 10**18

    assert collateral.balanceOf(alice) == 30 * 10**18
    assert collateral.balanceOf(amm) == 70 * 10**18

    assert market.user_state(alice)[:3] == (70 * 10**18, 0, 1500 * 10**18)
    assert market.total_debt() == 1500 * 10**18


def test_repay(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.close_loan(alice, market, {"from": alice})

    assert stable.totalSupply() == 0

    assert collateral.balanceOf(alice) == 100 * 10**18
    assert collateral.balanceOf(amm) == 0

    assert market.user_state(alice)[:3] == (0, 0, 0)
    assert market.total_debt() == 0


def test_repay_partial(market, amm, collateral, stable, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, 0, -600 * 10**18, {"from": alice})

    assert stable.totalSupply() == 400 * 10**18
    assert stable.balanceOf(alice) == 400 * 10**18

    assert collateral.balanceOf(alice) == 50 * 10**18
    assert collateral.balanceOf(amm) == 50 * 10**18

    assert market.user_state(alice)[:3] == (50 * 10**18, 0, 400 * 10**18)
    assert market.total_debt() == 400 * 10**18


def test_repay_unhealthy(controller, amm, market, oracle, stable, alice):
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    oracle.set_price(500 * 10**18, {"from": alice})
    stable.approve(amm, 2**256 - 1, {"from": alice})
    amm.exchange(0, 1, 50_000 * 10**18, 0, {"from": alice})

    assert market.health(alice) < 0
    controller.adjust_loan(alice, market, 0, -50_000 * 10**18, {"from": alice})

    assert stable.totalSupply() == 50_000 * 10**18
    assert stable.balanceOf(alice) == 0
    assert market.total_debt() == 50_000 * 10**18


@pytest.mark.parametrize("coll_change", [5 * 10**18, -8 * 10**18])
@pytest.mark.parametrize("debt_change", [10**20, -5 * 10**19])
def test_adjust_coll_and_debt(
    market, amm, collateral, stable, controller, alice, coll_change, debt_change
):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, coll_change, debt_change, {"from": alice})

    assert stable.totalSupply() == 1000 * 10**18 + debt_change
    assert stable.balanceOf(alice) == 1000 * 10**18 + debt_change

    assert collateral.balanceOf(alice) == 50 * 10**18 - coll_change
    assert collateral.balanceOf(amm) == 50 * 10**18 + coll_change

    assert market.user_state(alice)[:3] == (
        50 * 10**18 + coll_change,
        0,
        1000 * 10**18 + debt_change,
    )
    assert market.total_debt() == 1000 * 10**18 + debt_change


def test_open_zero_debt(market, controller, alice):
    with brownie.reverts("DFM:C 0 coll or debt"):
        controller.create_loan(alice, market, 50 * 10**18, 0, 5, {"from": alice})


def test_open_zero_coll(market, controller, alice):
    with brownie.reverts("DFM:C 0 coll or debt"):
        controller.create_loan(alice, market, 0, 1000 * 10**18, 5, {"from": alice})


def test_open_already_exists(market, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    with brownie.reverts("DFM:M Loan already exists"):
        controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})


def test_open_min_ticks(market, controller, alice):
    with brownie.reverts("DFM:M Need more ticks"):
        controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 3, {"from": alice})


def test_open_max_ticks(market, controller, alice):
    with brownie.reverts("DFM:M Need less ticks"):
        controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 51, {"from": alice})


def test_open_invalid_market(controller, alice):
    with brownie.reverts("DFM:C Invalid market"):
        controller.create_loan(alice, ZERO_ADDRESS, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})


def test_adjust_zero_change(market, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    with brownie.reverts("DFM:C No change"):
        controller.adjust_loan(alice, market, 0, 0, {"from": alice})


def test_adjust_invalid_market(controller, market, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    with brownie.reverts("DFM:C Invalid market"):
        controller.adjust_loan(alice, ZERO_ADDRESS, -100, -100, {"from": alice})


def test_adjust_not_exists(controller, market, alice):
    with brownie.reverts("DFM:M Loan doesn't exist"):
        controller.adjust_loan(alice, market, -100, -100, {"from": alice})


def test_adjust_no_remaining_debt(controller, market, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    with brownie.reverts("DFM:M No remaining debt"):
        controller.adjust_loan(alice, market, -50 * 10**18, -1000 * 10**18, {"from": alice})


def test_adjust_max_active_band(controller, market, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    with brownie.reverts("DFM:M band > max_active_band"):
        controller.adjust_loan(alice, market, 100, 100, -(2**255), {"from": alice})


def test_adjust_add_coll_unhealthy(controller, amm, market, oracle, stable, alice):
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    oracle.set_price(500 * 10**18, {"from": alice})
    stable.approve(amm, 2**256 - 1, {"from": alice})
    amm.exchange(0, 1, 100_000 * 10**18, 0, {"from": alice})

    with brownie.reverts("DFM:M Unhealthy loan, repay only"):
        controller.adjust_loan(alice, market, 50 * 10**18, 0, {"from": alice})


def test_adjust_increase_debt_unhealthy(controller, amm, market, oracle, stable, alice):
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    oracle.set_price(500 * 10**18, {"from": alice})
    stable.approve(amm, 2**256 - 1, {"from": alice})
    amm.exchange(0, 1, 100_000 * 10**18, 0, {"from": alice})

    with brownie.reverts("DFM:M Unhealthy loan, repay only"):
        controller.adjust_loan(alice, market, 0, 50_000 * 10**18, {"from": alice})


def test_close_invalid_market(controller, market, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    with brownie.reverts("DFM:C Invalid market"):
        controller.close_loan(alice, ZERO_ADDRESS, {"from": alice})


def test_close_not_exists(controller, market, alice):
    with brownie.reverts("DFM:M Loan doesn't exist"):
        controller.close_loan(alice, market, {"from": alice})
