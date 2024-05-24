from brownie import chain
import pytest
import brownie


MARKET_CEILING = 10_000 * 10**18
COLL_AMOUNT = 50 * 10**18


@pytest.fixture(scope="module", autouse=True)
def setup(stable, market, collateral, controller, alice, bob, deployer):

    for acct in (alice, bob):
        collateral._mint_for_testing(acct, COLL_AMOUNT * 2)
        collateral.approve(controller, 2**256 - 1, {"from": acct})

    # hacky but doesn't affect tests - alice needs extra stable for interest when closing loans
    stable.mint(alice, MARKET_CEILING, {"from": controller})

    market.set_debt_ceiling(MARKET_CEILING, {"from": deployer})


def test_initial_max_borrowable(market, controller):
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == MARKET_CEILING


def test_exceed_market_ceiling_create_loan(market, controller, alice):
    with brownie.reverts("DFM:M Exceeds debt ceiling"):
        controller.create_loan(alice, market, COLL_AMOUNT, MARKET_CEILING + 1, 5, {"from": alice})


def test_exceed_market_ceiling_adjust_loan(market, controller, alice):
    controller.create_loan(alice, market, COLL_AMOUNT, MARKET_CEILING // 2, 5, {"from": alice})
    with brownie.reverts("DFM:M Exceeds debt ceiling"):
        controller.adjust_loan(alice, market, 0, MARKET_CEILING // 2 + 1, {"from": alice})


def test_market_ceiling_open_loan(market, controller, alice):
    controller.create_loan(alice, market, COLL_AMOUNT, MARKET_CEILING, 5, {"from": alice})
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == 0


def test_market_ceiling_adjust_loan(market, controller, alice):
    amount = MARKET_CEILING // 2
    controller.create_loan(alice, market, COLL_AMOUNT, amount, 5, {"from": alice})
    controller.adjust_loan(alice, market, 0, amount, {"from": alice})
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == 0


def test_adjust_loan_reduce_debt_ceiling_not_applied(market, controller, policy, alice):
    policy.set_rate(1e18 / 365 / 86400, {"from": alice})
    controller.create_loan(alice, market, COLL_AMOUNT, MARKET_CEILING, 5, {"from": alice})

    # sleep for half a year, alice's debt should increase by roughly 50%
    chain.mine(timedelta=86400 * 31 * 6)
    assert market.total_debt() > MARKET_CEILING * 1.5

    # alice can repay partially, even tho total debt exceeds the ceiling after her action
    controller.adjust_loan(alice, market, 0, -MARKET_CEILING // 10, {"from": alice})
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == 0


def test_close_loan_ceiling_not_applied(market, controller, policy, alice, bob):
    policy.set_rate(1e18 / 365 / 86400, {"from": alice})

    controller.create_loan(bob, market, COLL_AMOUNT, MARKET_CEILING * 0.8, 5, {"from": bob})
    controller.create_loan(alice, market, COLL_AMOUNT, MARKET_CEILING * 0.1, 10, {"from": alice})

    # sleep for half a year, bob's debt is now well over the ceiling
    chain.mine(timedelta=86400 * 31 * 6)
    assert market.user_state(bob)[2] > MARKET_CEILING

    # alice can close her loan, even tho total debt exceeds the ceiling after her action
    controller.close_loan(alice, market, {"from": alice})
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == 0


def test_exceed_ceiling_from_accrued_interest(market, controller, policy, alice, bob):
    policy.set_rate(1e18 / 365 / 86400, {"from": alice})

    controller.create_loan(bob, market, COLL_AMOUNT, MARKET_CEILING * 0.8, 5, {"from": bob})

    # sleep for half a year, bob's debt is now well over the ceiling
    chain.mine(timedelta=86400 * 31 * 6)
    assert market.user_state(bob)[2] > MARKET_CEILING

    # alice's new loan would be under the debt ceiling if bob's interest were not considered
    # but it is considered so this tx will revert
    with brownie.reverts("DFM:M Exceeds debt ceiling"):
        controller.create_loan(
            alice, market, COLL_AMOUNT, MARKET_CEILING * 0.01, 5, {"from": alice}
        )


def test_set_ceiling_below_total_debt(market, controller, alice, deployer):
    controller.create_loan(alice, market, COLL_AMOUNT, MARKET_CEILING // 2, 5, {"from": alice})

    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == MARKET_CEILING // 2

    market.set_debt_ceiling(MARKET_CEILING // 4, {"from": deployer})
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == 0
