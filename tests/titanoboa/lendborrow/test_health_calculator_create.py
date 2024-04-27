import boa
from hypothesis import given
from hypothesis import strategies as st


@given(
    n=st.integers(min_value=5, max_value=50),
    debt=st.integers(min_value=10**10, max_value=2 * 10**6 * 10**18),
    collateral=st.integers(min_value=10**10, max_value=10**9 * 10**18 // 3000),
)
def test_health_calculator_create(
    amm, market, controller, collateral_token, collateral, debt, n, accounts
):
    user = accounts[1]
    calculator_fail = False
    try:
        health = market.health_calculator(user, collateral, debt, False, n)
        health_full = market.health_calculator(user, collateral, debt, True, n)
        assert (
            controller.get_pending_market_state_for_account(user, market, collateral, debt)[3]
            == health_full
        )
    except Exception:
        calculator_fail = True

    collateral_token._mint_for_testing(user, collateral)

    with boa.env.prank(user):
        try:
            market.create_loan(collateral, debt, n)
        except Exception:
            return
    assert not calculator_fail

    assert abs(market.health(user) - health) / 1e18 < n * 2e-5
    assert abs(market.health(user, True) - health_full) / 1e18 < n * 2e-5
