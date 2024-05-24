from brownie import chain
import pytest
import itertools


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, collateral2, collateral3, alice, bob, controller, policy):

    for acct, coll in itertools.product([alice, bob], [collateral, collateral2, collateral3]):
        coll._mint_for_testing(acct, 100 * 10**18)
        coll.approve(controller, 2**256 - 1, {"from": acct})

    policy.set_rate(1e18 / 365 / 86400, {"from": alice})


def test_one_loan(market, controller, alice):
    amount = 1000 * 10**18

    controller.create_loan(alice, market, 50 * 10**18, amount, 5, {"from": alice})
    ts = chain[-1].timestamp

    assert market.user_state(alice)[2] == amount
    assert market.total_debt() == amount
    assert controller.total_debt() == amount

    chain.mine(timedelta=86400)

    expected = amount + (amount * (chain[-1].timestamp - ts) / 365 / 86400)

    # market debt increases within view methods
    assert market.total_debt() == market.user_state(alice)[2]
    assert abs(market.total_debt() - expected) / expected < 1e-10

    # controller debt only updates when there is an interaction with each market
    assert controller.total_debt() == amount

    # collecting fees should update controller total debt
    controller.collect_fees([market], {"from": alice})
    expected = amount + (amount * (chain[-1].timestamp - ts) / 365 / 86400)

    assert market.total_debt() == market.user_state(alice)[2] == controller.total_debt()
    assert abs(market.total_debt() - expected) / expected < 1e-10


def test_multiple_loans(market, amm, controller, alice, bob):
    amount = 1000 * 10**18
    total = amount * 2

    controller.create_loan(alice, market, 50 * 10**18, amount, 5, {"from": alice})
    controller.create_loan(bob, market, 50 * 10**18, amount, 5, {"from": bob})

    chain.mine(timedelta=86400 - 1)

    # alice adjusts her collateral, which should update controller total debt
    controller.adjust_loan(alice, market, -1, 0, {"from": alice})
    assert market.total_debt() == controller.total_debt()
    assert (market.total_debt() - total) / total == pytest.approx(1 / 365, 1e-5)


def test_multiple_loans_different_markets(market, market2, market3, controller, alice, bob):
    market_list = [market, market2, market3]
    amount = 1000 * 10**18

    # alice and bob open loans in each market
    for c, (acct, mkt) in enumerate(itertools.product([alice, bob], market_list), start=1):
        controller.create_loan(acct, mkt, 50 * 10**18, amount * c, 5, {"from": acct})
        chain.mine(timedelta=42069 * c)

    assert min(i.pending_debt() for i in market_list) > 0
    assert controller.total_debt() == sum(i.total_debt() - i.pending_debt() for i in market_list)

    # interactions with each market at different timestamps
    controller.adjust_loan(alice, market, -1, 0, {"from": alice})
    chain.mine(timedelta=86400)
    controller.adjust_loan(bob, market2, 0, -amount // 2, {"from": bob})
    chain.mine(timedelta=86400)
    controller.close_loan(alice, market3, {"from": alice})
    chain.mine(timedelta=86400)

    total_debt = controller.total_debt()
    assert min(i.pending_debt() for i in market_list) > 0
    assert total_debt == sum(i.total_debt() - i.pending_debt() for i in market_list)

    # collecting fees without touching the markets should NOT affect controller total debt
    controller.collect_fees([], {"from": alice})
    assert controller.total_debt() == total_debt

    # collecting fees from every market, controller is perfectly sync'd with markets
    controller.collect_fees(market_list, {"from": alice})
    assert sum(i.pending_debt() for i in market_list) == 0
    assert controller.total_debt() == sum(i.total_debt() for i in market_list)
