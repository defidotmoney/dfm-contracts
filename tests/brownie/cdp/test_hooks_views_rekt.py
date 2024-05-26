import pytest

from brownie import ZERO_ADDRESS, chain


@pytest.fixture(scope="module", autouse=True)
def setup(hooks, collateral, controller, market, amm, stable, policy, alice, bob, deployer):
    for acct in [deployer, alice]:
        collateral._mint_for_testing(acct, 100 * 10**18)
        collateral.approve(controller, 2**256 - 1, {"from": acct})

    # approvals
    stable.approve(controller, 2**256 - 1, {"from": bob})
    stable.approve(amm, 2**256 - 1, {"from": deployer})

    hooks.set_configuration(2, [True, True, True, True], {"from": deployer})
    controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})

    # ensure initial hook debt is sufficient for negative adjustments
    stable.mint(deployer, 200 * 10**18, {"from": controller})
    controller.increase_hook_debt(ZERO_ADDRESS, hooks, 200 * 10**18, {"from": deployer})

    # set rate to 100% APR
    policy.set_rate(int(1e18 * 1.0 / 365 / 86400), {"from": alice})
    controller.create_loan(alice, market, 100 * 10**18, 200_000 * 10**18, 5, {"from": alice})

    # time travel 1 year, alice should now be very rekt
    chain.mine(timedelta=86400 * 365)

    # set rate to 0 and collect fees to apply rate change to market
    policy.set_rate(0, {"from": alice})
    controller.collect_fees([market], {"from": alice})

    # hacky mint stables to deployer for amm swap
    stable.mint(deployer, 10_000 * 10**18, {"from": controller})


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
@pytest.mark.parametrize("swap_coll", [True, False])
def test_liquidation(
    views,
    market,
    stable,
    collateral,
    amm,
    controller,
    alice,
    bob,
    deployer,
    hooks,
    adjustment,
    swap_coll,
):
    hooks.set_response(adjustment, {"from": alice})

    if swap_coll:
        amm.exchange(0, 1, 10_000 * 10**18, 0, {"from": deployer})

    actual = views.get_market_states_for_account(alice, [market])[0]
    # (account, debt repaid, debt burned from caller, debt burned from amm, coll received, hook adjustment)
    expected = views.get_liquidation_amounts(alice, market)
    assert len(expected) == 1
    expected = expected[0]

    assert expected[0] == alice

    debt = market.debt(alice)
    assert actual[1] == debt
    assert expected[1] == debt

    debt_amm, coll_amm = amm.get_sum_xy(alice)
    if swap_coll:
        assert debt_amm > 0
    else:
        assert debt_amm == 0

    assert actual[2] == coll_amm
    assert expected[4] == coll_amm

    assert actual[3] == debt_amm
    assert expected[3] == debt_amm

    assert expected[2] == debt - debt_amm + adjustment
    assert expected[5] == adjustment

    # mint bob just enough stable to perform the liquidation
    stable.mint(bob, expected[2], {"from": controller})
    controller.liquidate(market, alice, 0, {"from": bob})

    assert collateral.balanceOf(bob) == coll_amm
    assert stable.balanceOf(bob) == 0


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
@pytest.mark.parametrize("swap_coll", [True, False])
def test_close_loan_underwater(
    views,
    market,
    stable,
    collateral,
    amm,
    controller,
    alice,
    deployer,
    hooks,
    adjustment,
    swap_coll,
):
    hooks.set_response(adjustment, {"from": alice})

    if swap_coll:
        amm.exchange(0, 1, 10_000 * 10**18, 0, {"from": deployer})

    actual = views.get_market_states_for_account(alice, [market])[0]
    # (debt repaid, debt burned from owner, debt burned from amm, coll withdrawn, hook adjustment)
    expected = views.get_close_loan_amounts(alice, market)

    debt = market.debt(alice)
    assert actual[1] == debt
    assert expected[0] == debt

    debt_amm, coll_amm = amm.get_sum_xy(alice)
    if swap_coll:
        assert debt_amm > 0
    else:
        assert debt_amm == 0

    assert actual[2] == coll_amm
    assert expected[3] == coll_amm

    assert actual[3] == debt_amm
    assert expected[2] == debt_amm

    assert expected[1] == debt - debt_amm + adjustment
    assert expected[4] == adjustment

    # hacky mint alice enough stable to close the loan
    stable.mint(alice, expected[1] - stable.balanceOf(alice), {"from": controller})
    controller.close_loan(alice, market, {"from": alice})

    assert stable.balanceOf(alice) == 0
    assert collateral.balanceOf(alice) == expected[3]
