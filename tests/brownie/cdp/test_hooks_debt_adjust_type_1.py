import pytest

from brownie import ZERO_ADDRESS


HOOK_ADJUSTMENT = 200 * 10**18


@pytest.fixture(scope="module", autouse=True)
def setup(hooks, collateral, controller, market, stable, alice, deployer):
    for acct in [deployer, alice]:
        collateral._mint_for_testing(acct, 100 * 10**18)
        collateral.approve(controller, 2**256 - 1, {"from": acct})

    hooks.set_configuration(1, [True, True, True, True], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})


def test_create_loan_adjust(market, stable, fee_receiver, controller, alice, hooks):
    hooks.set_response(HOOK_ADJUSTMENT, {"from": alice})
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    # expect actual amounts
    assert stable.totalSupply() == 1000 * 10**18
    assert stable.balanceOf(alice) == 1000 * 10**18
    assert controller.minted() == 1000 * 10**18
    assert controller.redeemed() == 0
    assert controller.total_hook_debt() == 0
    assert stable.balanceOf(fee_receiver) == 0

    # expect adjusted amounts
    assert market.user_state(alice)[:3] == (50 * 10**18, 0, 1000 * 10**18 + HOOK_ADJUSTMENT)
    assert market.total_debt() == 1000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.total_debt() == 1000 * 10**18 + HOOK_ADJUSTMENT

    controller.collect_fees([], {"from": alice})

    assert stable.totalSupply() == 1000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.minted() == 1000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.redeemed() == 0
    assert controller.total_hook_debt() == 0
    assert stable.balanceOf(fee_receiver) == HOOK_ADJUSTMENT


def test_adjust_loan_increase_debt(market, hooks, stable, fee_receiver, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_response(HOOK_ADJUSTMENT, {"from": alice})
    controller.adjust_loan(alice, market, 0, 1000 * 10**18, {"from": alice})

    assert stable.totalSupply() == 2000 * 10**18
    assert stable.balanceOf(alice) == 2000 * 10**18
    assert controller.minted() == 2000 * 10**18
    assert controller.redeemed() == 0
    assert controller.total_hook_debt() == 0
    assert stable.balanceOf(fee_receiver) == 0

    assert market.user_state(alice)[:3] == (50 * 10**18, 0, 2000 * 10**18 + HOOK_ADJUSTMENT)
    assert market.total_debt() == 2000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.total_debt() == 2000 * 10**18 + HOOK_ADJUSTMENT

    controller.collect_fees([], {"from": alice})

    assert stable.totalSupply() == 2000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.minted() == 2000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.redeemed() == 0
    assert controller.total_hook_debt() == 0
    assert stable.balanceOf(fee_receiver) == HOOK_ADJUSTMENT


def test_adjust_loan_decrease_debt(market, hooks, stable, fee_receiver, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 3000 * 10**18, 5, {"from": alice})

    hooks.set_response(HOOK_ADJUSTMENT, {"from": alice})
    controller.adjust_loan(alice, market, 0, -1000 * 10**18, {"from": alice})

    assert stable.totalSupply() == 2000 * 10**18
    assert stable.balanceOf(alice) == 2000 * 10**18
    assert controller.minted() == 3000 * 10**18
    assert controller.redeemed() == 1000 * 10**18
    assert controller.total_hook_debt() == 0
    assert stable.balanceOf(fee_receiver) == 0

    assert market.user_state(alice)[:3] == (50 * 10**18, 0, 2000 * 10**18 + HOOK_ADJUSTMENT)
    assert market.total_debt() == 2000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.total_debt() == 2000 * 10**18 + HOOK_ADJUSTMENT

    controller.collect_fees([], {"from": alice})

    assert stable.totalSupply() == 2000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.minted() == 3000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.redeemed() == 1000 * 10**18
    assert controller.total_hook_debt() == 0
    assert stable.balanceOf(fee_receiver) == HOOK_ADJUSTMENT


def test_close_loan(market, hooks, stable, fee_receiver, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_response(HOOK_ADJUSTMENT, {"from": alice})
    if HOOK_ADJUSTMENT > 0:
        stable.mint(alice, HOOK_ADJUSTMENT, {"from": controller})

    controller.close_loan(alice, market, {"from": alice})

    assert stable.totalSupply() == 0
    assert controller.minted() == 1000 * 10**18
    assert controller.redeemed() == 1000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.total_hook_debt() == 0
    assert stable.balanceOf(fee_receiver) == 0

    assert market.user_state(alice)[:3] == (0, 0, 0)
    assert market.total_debt() == 0
    assert controller.total_debt() == 0

    controller.collect_fees([], {"from": alice})

    assert stable.totalSupply() == HOOK_ADJUSTMENT
    assert controller.minted() == 1000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.redeemed() == 1000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.total_hook_debt() == 0
    assert stable.balanceOf(fee_receiver) == HOOK_ADJUSTMENT


def test_liquidation(market, stable, fee_receiver, controller, oracle, alice, hooks):
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    oracle.set_price(2100 * 10**18, {"from": alice})

    hooks.set_response(HOOK_ADJUSTMENT, {"from": alice})
    if HOOK_ADJUSTMENT > 0:
        stable.mint(alice, HOOK_ADJUSTMENT, {"from": controller})

    controller.liquidate(market, alice, 0, {"from": alice})

    assert stable.totalSupply() == 0
    assert controller.minted() == 100_000 * 10**18
    assert controller.redeemed() == 100_000 * 10**18 + HOOK_ADJUSTMENT
    assert stable.balanceOf(fee_receiver) == 0

    assert market.user_state(alice)[:3] == (0, 0, 0)
    assert market.total_debt() == 0
    assert controller.total_debt() == 0

    controller.collect_fees([], {"from": alice})

    assert stable.totalSupply() == HOOK_ADJUSTMENT
    assert controller.minted() == 100_000 * 10**18 + HOOK_ADJUSTMENT
    assert controller.redeemed() == 100_000 * 10**18 + HOOK_ADJUSTMENT
    assert stable.balanceOf(fee_receiver) == HOOK_ADJUSTMENT
