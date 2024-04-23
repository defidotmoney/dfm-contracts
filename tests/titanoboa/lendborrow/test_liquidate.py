import pytest
import boa
from boa.vyper.contract import BoaError
from hypothesis import given, settings
from hypothesis import strategies as st
from ..conftest import approx


N = 5


@pytest.fixture(scope="module")
def controller_for_liquidation(
    stablecoin,
    collateral_token,
    market,
    controller,
    amm,
    price_oracle,
    monetary_policy,
    admin,
    fee_receiver,
    accounts,
):
    def f(sleep_time, discount):
        user = admin
        user2 = accounts[2]
        collateral_amount = 10**18
        with boa.env.prank(admin):
            market.set_amm_fee(10**6)
            monetary_policy.set_rate(int(1e18 * 1.0 / 365 / 86400))  # 100% APY
            collateral_token._mint_for_testing(user, collateral_amount)
            collateral_token._mint_for_testing(user2, collateral_amount)
            stablecoin.approve(amm, 2**256 - 1)
            stablecoin.approve(controller, 2**256 - 1)
            collateral_token.approve(controller, 2**256 - 1)
        with boa.env.prank(user2):
            collateral_token.approve(controller, 2**256 - 1)
        debt = market.max_borrowable(collateral_amount, N)

        with boa.env.prank(user):
            controller.create_loan(user, market, collateral_amount, debt, N)
        health_0 = market.health(user)
        # We put mostly USD into AMM, and its quantity remains constant while
        # interest is accruing. Therefore, we will be at liquidation at some point
        with boa.env.prank(user):
            amm.exchange(0, 1, debt, 0)
        health_1 = market.health(user)

        assert health_0 <= health_1  # Earns fees on dynamic fee

        boa.env.time_travel(sleep_time)

        health_2 = market.health(user)
        # Still healthy but liquidation threshold satisfied
        assert health_2 < discount
        if discount > 0:
            assert health_2 > 0

        with boa.env.prank(admin):
            # Stop charging fees to have enough coins to liquidate in existence a block before
            monetary_policy.set_rate(0)

            controller.collect_fees([market.address])
            # Check that we earned the same in admin fees as we need to liquidate
            # Calculation is not precise because of dead shares, but the last withdrawal will put dust in admin fees
            assert approx(
                stablecoin.balanceOf(fee_receiver),
                market.tokens_to_liquidate(user),
                1e-10,
            )

        # Borrow some more funds to repay for our overchargings with DEAD_SHARES
        with boa.env.prank(user2):
            controller.create_loan(user2, market, collateral_amount, debt, N)

        return market

    return f


def test_liquidate(
    accounts, admin, controller_for_liquidation, amm, stablecoin, controller, fee_receiver
):
    user = admin

    market = controller_for_liquidation(sleep_time=80 * 86400, discount=0)
    x = amm.get_sum_xy(user)[0]

    with boa.env.prank(accounts[2]):
        stablecoin.transfer(fee_receiver, 10**10)

    with boa.env.prank(fee_receiver):
        with boa.reverts("DFM:M Slippage"):
            controller.liquidate(market.address, user, x + 1)
        controller.liquidate(market.address, user, int(x * 0.999999))


def test_self_liquidate(
    accounts, admin, controller_for_liquidation, amm, stablecoin, fee_receiver, controller
):
    user = admin

    with boa.env.anchor():
        market = controller_for_liquidation(sleep_time=40 * 86400, discount=2.5 * 10**16)

        with boa.env.prank(accounts[2]):
            stablecoin.transfer(fee_receiver, 10**10)

        x = amm.get_sum_xy(user)[0]
        with boa.env.prank(fee_receiver):
            stablecoin.transfer(user, stablecoin.balanceOf(fee_receiver))

        with boa.env.prank(accounts[1]):
            with boa.reverts("DFM:M Not enough rekt"):
                controller.liquidate(market.address, user, 0)

        with boa.env.prank(user):
            with boa.reverts("DFM:M Slippage"):
                controller.liquidate(market.address, user, x + 1)

            controller.liquidate(market.address, user, int(x * 0.999999))


@given(frac=st.integers(min_value=10**14, max_value=10**18 - 13))
def test_tokens_to_liquidate(
    accounts, admin, controller, controller_for_liquidation, amm, stablecoin, frac, fee_receiver
):
    user = admin

    with boa.env.anchor():
        market = controller_for_liquidation(sleep_time=80 * 86400, discount=0)
        initial_balance = stablecoin.balanceOf(fee_receiver)
        tokens_to_liquidate = market.tokens_to_liquidate(user, frac)

        with boa.env.prank(accounts[2]):
            stablecoin.transfer(fee_receiver, 10**10)

        with boa.env.prank(fee_receiver):
            controller.liquidate(market, user, 0)

        balance = stablecoin.balanceOf(fee_receiver)

        if frac < 10**18:
            assert approx(balance, initial_balance - tokens_to_liquidate, 1e5, abs_precision=1e5)
        else:
            assert balance != initial_balance - tokens_to_liquidate
