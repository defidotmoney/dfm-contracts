import pytest
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(agg_policy, controller, stable, collateral, collateral2, alice, deployer):
    controller.change_existing_monetary_policy(agg_policy, 0, {"from": deployer})

    stable.mint(alice, 10_000_000 * 10**18, {"from": controller})
    for token in [collateral, collateral2]:
        token._mint_for_testing(alice, 10**24)
        token.approve(controller, 2**256 - 1, {"from": alice})


def test_increase_debt(agg_policy, market, controller, alice):
    rate = agg_policy.rate(market)
    new_rate = agg_policy.rate_after_debt_change(market, 9_000_000 * 10**18)
    assert new_rate > rate > 0

    controller.create_loan(alice, market, 10**24, 9_000_000 * 10**18, 10, {"from": alice})
    assert agg_policy.rate(market) == new_rate


def test_increase_with_multiple_markets(agg_policy, market, market2, controller, alice):
    controller.create_loan(alice, market2, 10**24, 5_000_000 * 10**18, 10, {"from": alice})

    rate = agg_policy.rate(market)
    new_rate = agg_policy.rate_after_debt_change(market, 9_000_000 * 10**18)
    assert new_rate > rate > 0

    controller.create_loan(alice, market, 10**24, 9_000_000 * 10**18, 10, {"from": alice})
    assert agg_policy.rate(market) == new_rate


def test_decrease_debt(agg_policy, market, controller, alice):
    controller.create_loan(alice, market, 10**24, 9_000_000 * 10**18, 10, {"from": alice})

    rate = agg_policy.rate(market)
    new_rate = agg_policy.rate_after_debt_change(market, -4_000_000 * 10**18)
    assert rate > new_rate > 0

    controller.adjust_loan(alice, market, 0, -4_000_000 * 10**18, {"from": alice})

    # cannot check direct equality because accrued interest pushes the rate up
    assert 50 > agg_policy.rate(market) - new_rate > 0


def test_decrease_with_multiple_markets(agg_policy, market, market2, controller, alice):
    controller.create_loan(alice, market2, 10**24, 5_000_000 * 10**18, 10, {"from": alice})
    controller.create_loan(alice, market, 10**24, 9_000_000 * 10**18, 10, {"from": alice})

    rate = agg_policy.rate(market)
    new_rate = agg_policy.rate_after_debt_change(market, -4_000_000 * 10**18)
    assert rate > new_rate > 0

    controller.adjust_loan(alice, market, 0, -4_000_000 * 10**18, {"from": alice})

    assert 50 > agg_policy.rate(market) - new_rate > 0


def test_decrease_bounded_total_debt(agg_policy, market, market2, controller, alice):
    controller.create_loan(alice, market2, 10**24, 100_000 * 10**18, 10, {"from": alice})
    controller.create_loan(alice, market, 10**24, 9_000_000 * 10**18, 10, {"from": alice})

    # sleeping for a year puts the controller's total debt out of sync with the market
    # this way we can test the controller total debt flooring within `agg_policy`
    chain.mine(timedelta=86400 * 365)
    assert controller.total_debt() < 10_000_000 * 10**18
    assert market.total_debt() > 10_000_000 * 10**18

    rate = agg_policy.rate(market)
    new_rate = agg_policy.rate_after_debt_change(market, -10_000_000 * 10**18)
    assert rate > new_rate > 0

    controller.adjust_loan(alice, market, 0, -10_000_000 * 10**18, {"from": alice})

    assert 50 > agg_policy.rate(market) - new_rate > 0
