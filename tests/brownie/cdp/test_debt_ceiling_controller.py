from brownie import chain
import pytest
import brownie
import itertools

MARKET_CEILING = 10_000 * 10**18
INITIAL_DEBT = 7_500 * 10**18
GLOBAL_CEILING = 15_000 * 10**18
REMAINING_DEBT = GLOBAL_CEILING - INITIAL_DEBT
COLL_AMOUNT = 50 * 10**18


@pytest.fixture(scope="module", autouse=True)
def setup(stable, market_list, collateral_list, controller, alice, bob, deployer):
    for acct, coll in itertools.product([alice, bob], collateral_list):
        coll._mint_for_testing(acct, 100 * 10**18)
        coll.approve(controller, 2**256 - 1, {"from": acct})

    # hacky but doesn't affect tests - alice needs extra stable for interest when closing loans
    stable.mint(alice, MARKET_CEILING, {"from": controller})

    for mkt in market_list:
        mkt.set_debt_ceiling(MARKET_CEILING, {"from": deployer})

    controller.set_global_market_debt_ceiling(GLOBAL_CEILING, {"from": deployer})

    controller.create_loan(alice, market_list[2], COLL_AMOUNT, INITIAL_DEBT, 5, {"from": alice})


def test_initial_max_borrowable(market, market2, market3, controller):
    assert controller.max_borrowable(market3, COLL_AMOUNT, 5) == MARKET_CEILING - INITIAL_DEBT
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == REMAINING_DEBT
    assert controller.max_borrowable(market2, COLL_AMOUNT, 5) == REMAINING_DEBT


def test_exceed_ceiling_create_loan(market, controller, alice):
    with brownie.reverts("DFM:C global debt ceiling"):
        controller.create_loan(alice, market, COLL_AMOUNT, REMAINING_DEBT + 1, 5, {"from": alice})

    with brownie.reverts("DFM:C global debt ceiling"):
        controller.create_loan(alice, market, COLL_AMOUNT, MARKET_CEILING, 5, {"from": alice})

    with brownie.reverts("DFM:M Exceeds debt ceiling"):
        controller.create_loan(alice, market, COLL_AMOUNT, MARKET_CEILING + 1, 5, {"from": alice})


def test_exceed_ceiling_adjust_loan(market, controller, alice):
    controller.create_loan(alice, market, COLL_AMOUNT, REMAINING_DEBT // 2, 5, {"from": alice})
    with brownie.reverts("DFM:C global debt ceiling"):
        controller.adjust_loan(alice, market, 0, REMAINING_DEBT // 2 + 1, {"from": alice})


def test_ceiling_open_loan(market, market2, market3, controller, alice):
    controller.create_loan(alice, market, COLL_AMOUNT, REMAINING_DEBT, 5, {"from": alice})

    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == 0
    assert controller.max_borrowable(market2, COLL_AMOUNT, 5) == 0
    assert controller.max_borrowable(market3, COLL_AMOUNT, 5) == 0


def test_market_ceiling_adjust_loan(market, controller, alice):
    amount = REMAINING_DEBT // 2
    controller.create_loan(alice, market, COLL_AMOUNT, amount, 5, {"from": alice})
    controller.adjust_loan(alice, market, 0, amount, {"from": alice})
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == 0


def test_adjust_loan_reduce_debt_ceiling_not_applied(market, market3, controller, policy, alice):
    controller.create_loan(alice, market, COLL_AMOUNT, REMAINING_DEBT, 5, {"from": alice})
    policy.set_rate(1e18 / 365 / 86400, {"from": alice})

    # collect fees to apply the new interest rate
    controller.collect_fees([market, market3])

    # sleep for half a year, alice's debt should increase by roughly 50%
    chain.mine(timedelta=86400 * 31 * 6)

    # controller total debt does not accrue interest automatically
    assert controller.total_debt() == GLOBAL_CEILING

    # collect fees again to bump controller total debt
    controller.collect_fees([market, market3])
    assert controller.total_debt() > GLOBAL_CEILING * 1.5

    # alice can repay partially, even tho total debt exceeds the ceiling after her action
    controller.adjust_loan(alice, market, 0, -MARKET_CEILING // 10, {"from": alice})
    assert controller.total_debt() > GLOBAL_CEILING
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == 0


def test_close_loan_ceiling_not_applied(market, market2, market3, controller, policy, alice):
    controller.create_loan(alice, market, COLL_AMOUNT, REMAINING_DEBT * 0.9, 5, {"from": alice})
    controller.create_loan(alice, market2, COLL_AMOUNT, REMAINING_DEBT * 0.1, 5, {"from": alice})
    policy.set_rate(1e18 / 365 / 86400, {"from": alice})

    # collect fees to apply the new interest rate
    controller.collect_fees([market, market2, market3])

    # sleep for two years, all debts are so big now!
    chain.mine(timedelta=86400 * 365 * 2)
    assert market3.user_state(alice)[2] > GLOBAL_CEILING

    # controller total debt does not accrue interest automatically
    assert controller.total_debt() == GLOBAL_CEILING

    # collect fees again to bump controller total debt
    controller.collect_fees([market, market3])
    assert controller.total_debt() > GLOBAL_CEILING * 2

    # # alice can close her loan, even tho total debt exceeds the ceiling after her action
    controller.close_loan(alice, market2, {"from": alice})
    assert controller.max_borrowable(market2, COLL_AMOUNT, 5) == 0


def test_set_ceiling_below_total_debt(market, market3, controller, deployer):
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == REMAINING_DEBT
    assert controller.max_borrowable(market3, COLL_AMOUNT, 5) == MARKET_CEILING - INITIAL_DEBT

    controller.set_global_market_debt_ceiling(MARKET_CEILING - INITIAL_DEBT, {"from": deployer})

    # `market` has no debt, but still cannot borrow because of debt on `market3`
    assert controller.max_borrowable(market, COLL_AMOUNT, 5) == 0

    # `market3` debt exceeds the controller ceiling
    assert controller.max_borrowable(market3, COLL_AMOUNT, 5) == 0
