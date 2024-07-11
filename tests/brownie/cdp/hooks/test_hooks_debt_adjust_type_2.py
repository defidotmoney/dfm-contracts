import pytest

from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(hooks, collateral, controller, market, stable, alice, deployer):
    for acct in [deployer, alice]:
        collateral._mint_for_testing(acct, 100 * 10**18)
        collateral.approve(controller, 2**256 - 1, {"from": acct})

    hooks.set_configuration(2, [True, True, True, True], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})

    # ensure initial hook debt is sufficient for negative adjustments
    stable.mint(deployer, 200 * 10**18, {"from": controller})
    controller.increase_hook_debt(ZERO_ADDRESS, hooks, 200 * 10**18, {"from": deployer})


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_create_loan_adjust(market, stable, fee_receiver, controller, alice, hooks, adjustment):
    hooks.set_response(adjustment, {"from": alice})
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    for _ in range(2):
        # expect actual amounts
        assert stable.totalSupply() == 1000 * 10**18
        assert stable.balanceOf(alice) == 1000 * 10**18
        assert controller.minted() == 1000 * 10**18
        assert controller.redeemed() == 200 * 10**18
        assert controller.total_hook_debt() == 200 * 10**18 + adjustment

        # expect adjusted amounts
        assert market.user_state(alice)[:3] == (50 * 10**18, 0, 1000 * 10**18 + adjustment)
        assert market.total_debt() == 1000 * 10**18 + adjustment
        assert controller.total_debt() == 1000 * 10**18 + adjustment

        # iterate to perform checks before and after collecting fees
        # for this hook type, there should never be any fees to collect
        controller.collect_fees([], {"from": alice})
        assert stable.balanceOf(fee_receiver) == 0


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_adjust_loan_increase_debt(
    market, hooks, stable, fee_receiver, controller, alice, adjustment
):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_response(adjustment, {"from": alice})
    controller.adjust_loan(alice, market, 0, 1000 * 10**18, {"from": alice})

    for _ in range(2):
        assert stable.totalSupply() == 2000 * 10**18
        assert stable.balanceOf(alice) == 2000 * 10**18
        assert controller.minted() == 2000 * 10**18
        assert controller.redeemed() == 200 * 10**18
        assert controller.total_hook_debt() == 200 * 10**18 + adjustment

        assert market.user_state(alice)[:3] == (50 * 10**18, 0, 2000 * 10**18 + adjustment)
        assert market.total_debt() == 2000 * 10**18 + adjustment
        assert controller.total_debt() == 2000 * 10**18 + adjustment

        controller.collect_fees([], {"from": alice})
        assert stable.balanceOf(fee_receiver) == 0


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_adjust_loan_decrease_debt(
    market, hooks, stable, fee_receiver, controller, alice, adjustment
):
    controller.create_loan(alice, market, 50 * 10**18, 3000 * 10**18, 5, {"from": alice})

    hooks.set_response(adjustment, {"from": alice})
    controller.adjust_loan(alice, market, 0, -1000 * 10**18, {"from": alice})

    for _ in range(2):
        assert stable.totalSupply() == 2000 * 10**18
        assert stable.balanceOf(alice) == 2000 * 10**18
        assert controller.minted() == 3000 * 10**18
        assert controller.redeemed() == 1000 * 10**18 + 200 * 10**18
        assert controller.total_hook_debt() == 200 * 10**18 + adjustment

        assert market.user_state(alice)[:3] == (50 * 10**18, 0, 2000 * 10**18 + adjustment)
        assert market.total_debt() == 2000 * 10**18 + adjustment
        assert controller.total_debt() == 2000 * 10**18 + adjustment

        controller.collect_fees([], {"from": alice})
        assert stable.balanceOf(fee_receiver) == 0


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_close_loan(market, hooks, stable, fee_receiver, controller, alice, adjustment):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    hooks.set_response(adjustment, {"from": alice})
    if adjustment > 0:
        stable.mint(alice, adjustment, {"from": controller})

    controller.close_loan(alice, market, {"from": alice})

    for _ in range(2):
        assert stable.totalSupply() == 0 + max(-adjustment, 0)
        assert controller.minted() == 1000 * 10**18
        assert controller.redeemed() == 200 * 10**18 + 1000 * 10**18 + adjustment
        assert controller.total_hook_debt() == 200 * 10**18 + adjustment

        assert market.user_state(alice)[:3] == (0, 0, 0)
        assert market.total_debt() == 0
        assert controller.total_debt() == 0

        controller.collect_fees([], {"from": alice})
        assert stable.balanceOf(fee_receiver) == 0


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_liquidation(market, stable, fee_receiver, controller, oracle, alice, hooks, adjustment):
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    oracle.set_price(2100 * 10**18, {"from": alice})

    hooks.set_response(adjustment, {"from": alice})
    if adjustment > 0:
        stable.mint(alice, adjustment, {"from": controller})

    controller.liquidate(market, alice, 0, {"from": alice})

    for _ in range(2):
        assert stable.totalSupply() == 0 + max(-adjustment, 0)
        assert controller.minted() == 100_000 * 10**18
        assert controller.redeemed() == 200 * 10**18 + 100_000 * 10**18 + adjustment
        assert controller.total_hook_debt() == 200 * 10**18 + adjustment

        assert market.user_state(alice)[:3] == (0, 0, 0)
        assert market.total_debt() == 0
        assert controller.total_debt() == 0

        controller.collect_fees([], {"from": alice})
        assert stable.balanceOf(fee_receiver) == 0
