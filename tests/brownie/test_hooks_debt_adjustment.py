import pytest

from brownie import ZERO_ADDRESS

INITIAL_FEES = 10_000 * 10**18


@pytest.fixture(scope="module", autouse=True)
def setup(hooks, collateral, controller, market, alice, deployer):
    for acct in [deployer, alice]:
        collateral._mint_for_testing(acct, 100 * 10**18)
        collateral.approve(controller, 2**256 - 1, {"from": acct})

    controller.set_market_hooks(ZERO_ADDRESS, hooks, [True, True, True, True], {"from": deployer})

    # magic to ensure we have non-zero fees, so negative debt adjustments don't underflow
    hooks.set_response(INITIAL_FEES, {"from": deployer})
    controller.create_loan(deployer, market, 100 * 10**18, INITIAL_FEES, 5, {"from": deployer})
    hooks.set_response(0, {"from": deployer})
    controller.adjust_loan(deployer, market, 0, -INITIAL_FEES, {"from": deployer})


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_create_loan_adjust(market, stable, fee_receiver, controller, alice, hooks, adjustment):
    hooks.set_response(adjustment, {"from": alice})
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    # expect actual amounts
    assert stable.totalSupply() == 1000 * 10**18
    assert stable.balanceOf(alice) == 1000 * 10**18
    assert controller.minted() == INITIAL_FEES + 1000 * 10**18
    assert controller.redeemed() == INITIAL_FEES

    # expect adjusted amounts
    assert market.user_state(alice)[:3] == (50 * 10**18, 0, 1000 * 10**18 + adjustment)
    assert market.total_debt() == INITIAL_FEES + 1000 * 10**18 + adjustment
    assert controller.total_debt() == INITIAL_FEES + 1000 * 10**18 + adjustment

    controller.collect_fees([], {"from": alice})

    assert stable.totalSupply() == INITIAL_FEES + 1000 * 10**18 + adjustment
    assert stable.balanceOf(fee_receiver) == INITIAL_FEES + adjustment
    assert market.total_debt() == INITIAL_FEES + 1000 * 10**18 + adjustment
    assert controller.total_debt() == INITIAL_FEES + 1000 * 10**18 + adjustment
    assert controller.minted() == INITIAL_FEES * 2 + 1000 * 10**18 + adjustment
    assert controller.redeemed() == INITIAL_FEES


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_adjust_loan_increase_debt(
    market, hooks, stable, fee_receiver, controller, alice, adjustment
):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_response(adjustment, {"from": alice})
    controller.adjust_loan(alice, market, 0, 1000 * 10**18, {"from": alice})

    assert stable.totalSupply() == 2000 * 10**18
    assert stable.balanceOf(alice) == 2000 * 10**18
    assert controller.minted() == INITIAL_FEES + 2000 * 10**18
    assert controller.redeemed() == INITIAL_FEES

    assert market.user_state(alice)[:3] == (50 * 10**18, 0, 2000 * 10**18 + adjustment)
    assert market.total_debt() == INITIAL_FEES + 2000 * 10**18 + adjustment
    assert controller.total_debt() == INITIAL_FEES + 2000 * 10**18 + adjustment

    controller.collect_fees([], {"from": alice})

    assert stable.totalSupply() == INITIAL_FEES + 2000 * 10**18 + adjustment
    assert stable.balanceOf(fee_receiver) == INITIAL_FEES + adjustment
    assert market.total_debt() == INITIAL_FEES + 2000 * 10**18 + adjustment
    assert controller.total_debt() == INITIAL_FEES + 2000 * 10**18 + adjustment
    assert controller.minted() == INITIAL_FEES * 2 + 2000 * 10**18 + adjustment
    assert controller.redeemed() == INITIAL_FEES


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_adjust_loan_decrease_debt(
    market, hooks, stable, fee_receiver, controller, alice, adjustment
):
    controller.create_loan(alice, market, 50 * 10**18, 3000 * 10**18, 5, {"from": alice})

    hooks.set_response(adjustment, {"from": alice})
    controller.adjust_loan(alice, market, 0, -1000 * 10**18, {"from": alice})

    assert stable.totalSupply() == 2000 * 10**18
    assert stable.balanceOf(alice) == 2000 * 10**18
    assert controller.minted() == INITIAL_FEES + 3000 * 10**18
    assert controller.redeemed() == INITIAL_FEES + 1000 * 10**18

    assert market.user_state(alice)[:3] == (50 * 10**18, 0, 2000 * 10**18 + adjustment)
    assert market.total_debt() == INITIAL_FEES + 2000 * 10**18 + adjustment
    assert controller.total_debt() == INITIAL_FEES + 2000 * 10**18 + adjustment

    controller.collect_fees([], {"from": alice})

    assert stable.totalSupply() == INITIAL_FEES + 2000 * 10**18 + adjustment
    assert stable.balanceOf(fee_receiver) == INITIAL_FEES + adjustment
    assert market.total_debt() == INITIAL_FEES + 2000 * 10**18 + adjustment
    assert controller.total_debt() == INITIAL_FEES + 2000 * 10**18 + adjustment
    assert controller.minted() == INITIAL_FEES * 2 + 3000 * 10**18 + adjustment
    assert controller.redeemed() == INITIAL_FEES + 1000 * 10**18


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_close_loan(market, hooks, stable, fee_receiver, controller, alice, adjustment):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_response(adjustment, {"from": alice})
    if adjustment > 0:
        stable.mint(alice, adjustment, {"from": controller})

    controller.close_loan(alice, market, {"from": alice})

    assert stable.totalSupply() == 0 + max(-adjustment, 0)
    assert controller.minted() == INITIAL_FEES + 1000 * 10**18
    assert controller.redeemed() == INITIAL_FEES + 1000 * 10**18 + adjustment

    assert market.user_state(alice)[:3] == (0, 0, 0)
    assert market.total_debt() == INITIAL_FEES
    assert controller.total_debt() == INITIAL_FEES

    controller.collect_fees([], {"from": alice})

    assert stable.totalSupply() == INITIAL_FEES + max(adjustment, 0)
    assert stable.balanceOf(fee_receiver) == INITIAL_FEES + adjustment
    assert market.total_debt() == INITIAL_FEES
    assert controller.total_debt() == INITIAL_FEES
    assert controller.minted() == INITIAL_FEES * 2 + 1000 * 10**18 + adjustment
    assert controller.redeemed() == INITIAL_FEES + 1000 * 10**18 + adjustment

    if adjustment < 0:
        assert stable.balanceOf(alice) == -adjustment


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_liquidation(market, stable, fee_receiver, controller, oracle, alice, hooks, adjustment):
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    oracle.set_price(2100 * 10**18, {"from": alice})

    hooks.set_response(adjustment, {"from": alice})
    if adjustment > 0:
        stable.mint(alice, adjustment, {"from": controller})

    controller.liquidate(market, alice, 0, {"from": alice})

    assert stable.totalSupply() == 0 + max(-adjustment, 0)
    assert controller.minted() == INITIAL_FEES + 100_000 * 10**18
    assert controller.redeemed() == INITIAL_FEES + 100_000 * 10**18 + adjustment

    assert market.user_state(alice)[:3] == (0, 0, 0)
    assert market.total_debt() == INITIAL_FEES
    assert controller.total_debt() == INITIAL_FEES

    controller.collect_fees([], {"from": alice})

    assert stable.totalSupply() == INITIAL_FEES + max(adjustment, 0)
    assert stable.balanceOf(fee_receiver) == INITIAL_FEES + adjustment
    assert market.total_debt() == INITIAL_FEES
    assert controller.total_debt() == INITIAL_FEES
    assert controller.minted() == INITIAL_FEES * 2 + 100_000 * 10**18 + adjustment
    assert controller.redeemed() == INITIAL_FEES + 100_000 * 10**18 + adjustment

    if adjustment < 0:
        assert stable.balanceOf(alice) == -adjustment
