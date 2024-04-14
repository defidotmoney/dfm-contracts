import pytest
import brownie
from brownie import chain, ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, alice, controller, market, policy):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})

    # set rate to 100% APR
    policy.set_rate(int(1e18 * 1.0 / 365 / 86400), {"from": alice})
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})

    # time travel 1 year, alice should now be liquidatable
    chain.mine(timedelta=86400 * 365)

    # set rate to 0 and collect fees to apply rate change to market
    # this way we can mint exactly the needed `stable` for liquidation
    policy.set_rate(0, {"from": alice})
    controller.collect_fees([market], {"from": alice})


def test_liquidation(market, stable, controller, policy, fee_receiver, alice, bob):
    # hacky mint
    debt = controller.get_market_state_for_account(market, alice)[0]
    stable.mint(bob, debt, {"from": controller})

    # liquidation time
    controller.liquidate(market, alice, 0, {"from": bob})

    assert stable.totalSupply() == debt
    assert stable.balanceOf(alice) == 100_000 * 10**18
    assert stable.balanceOf(bob) == 0
    assert stable.balanceOf(fee_receiver) == debt - 100_000 * 10**18

    assert controller.minted() == debt
    assert controller.redeemed() == debt

    assert market.user_state(alice)[:3] == (0, 0, 0)
    assert market.total_debt() == 0
    assert controller.total_debt() == 0


@pytest.mark.parametrize("frac", [10**17, 123456789, 4 * 10**13])
def test_partial_liquidation(market, stable, controller, policy, fee_receiver, alice, bob, frac):
    # hacky mint
    debt = controller.get_market_state_for_account(market, alice)[0]
    liquidation_amount = debt * frac // 10**18
    stable.mint(bob, liquidation_amount, {"from": controller})

    # liquidation time
    controller.liquidate(market, alice, 0, frac, {"from": bob})

    assert stable.totalSupply() == debt
    assert stable.balanceOf(alice) == 100_000 * 10**18
    assert stable.balanceOf(bob) == 0
    assert stable.balanceOf(controller) == 0
    assert stable.balanceOf(fee_receiver) == debt - 100_000 * 10**18

    assert controller.minted() == debt
    assert controller.redeemed() == liquidation_amount

    assert market.user_state(alice)[2] == debt - liquidation_amount
    assert market.total_debt() == debt - liquidation_amount
    assert controller.total_debt() == debt - liquidation_amount


@pytest.mark.parametrize("frac", [10**18 + 1, 2**255 - 1, 2**256 - 1])
def test_frac_too_high(market, stable, controller, alice, bob, frac):
    # hacky mint
    debt = controller.get_market_state_for_account(market, alice)[0]
    stable.mint(bob, debt, {"from": controller})

    with brownie.reverts("DFM:C frac too high"):
        controller.liquidate(market, alice, 0, frac, {"from": bob})


def test_frac_zero(market, stable, controller, alice, bob):
    # hacky mint
    debt = controller.get_market_state_for_account(market, alice)[0]
    stable.mint(bob, debt, {"from": controller})

    with brownie.reverts("DFM:M No Debt"):
        controller.liquidate(market, alice, 0, 0, {"from": bob})


def test_invalid_market(controller, alice):
    with brownie.reverts("DFM:C Invalid market"):
        controller.liquidate(ZERO_ADDRESS, alice, 0, {"from": alice})


def test_slippage(market, stable, controller, alice, bob):
    debt = controller.get_market_state_for_account(market, alice)[0]
    stable.mint(bob, debt, {"from": controller})

    with brownie.reverts("DFM:M Slippage"):
        controller.liquidate(market, alice, 51 * 10**18, {"from": bob})
