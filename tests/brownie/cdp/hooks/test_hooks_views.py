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
@pytest.mark.parametrize("num_bands", [5, 33, 50])
def test_create_loan_adjust(views, market, amm, controller, alice, hooks, adjustment, num_bands):
    hooks.set_response(adjustment, {"from": alice})

    expected = views.get_pending_market_state_for_account(
        alice, market, 50 * 10**18, 1000 * 10**18, num_bands
    )

    assert expected["account_debt"] == 1000 * 10**18 + adjustment
    assert expected["amm_coll_balance"] == 50 * 10**18
    assert expected["amm_stable_balance"] == 0
    assert expected["hook_debt_adjustment"] == adjustment

    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, num_bands, {"from": alice})

    # (market, account debt, amm coll balance, amm stable balance, health, bands, liquidation range)
    actual = views.get_market_states_for_account(alice, [market])[0]

    health = market.health(alice, True)
    assert actual[4] == health
    assert abs(health - expected["health"]) / 1e18 < 1e-10

    bands_amm = amm.read_user_tick_numbers(alice)
    bands_views = views.get_market_amm_bands_for_account(alice, market)
    assert bands_amm == (bands_views[0]["band_num"], bands_views[-1]["band_num"])
    assert expected["bands"] == bands_amm
    assert len(bands_views) == bands_amm[1] - bands_amm[0] + 1
    assert sum(i["coll_balance"] for i in bands_views) == 50 * 10**18
    assert sum(i["debt_balance"] for i in bands_views) == 0

    coll_conversion_range = market.user_prices(alice)
    assert coll_conversion_range == (
        bands_views[0]["price_range"][1],
        bands_views[-1]["price_range"][0],
    )
    assert actual["coll_conversion_range"] == coll_conversion_range
    assert expected["coll_conversion_range"] == coll_conversion_range


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
@pytest.mark.parametrize("num_bands", [0, 5, 10, 100])
def test_adjust_loan_increase_debt(
    views, market, hooks, amm, controller, alice, adjustment, num_bands
):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    hooks.set_response(adjustment, {"from": alice})

    # num_bands should be ignored
    expected = views.get_pending_market_state_for_account(
        alice, market, 0, 1000 * 10**18, num_bands
    )

    assert expected["account_debt"] == 2000 * 10**18 + adjustment
    assert expected["amm_coll_balance"] == 50 * 10**18
    assert expected["amm_stable_balance"] == 0
    assert expected["hook_debt_adjustment"] == adjustment

    controller.adjust_loan(alice, market, 0, 1000 * 10**18, {"from": alice})

    # (market, account debt, amm coll balance, amm stable balance, health, bands, liquidation range)
    actual = views.get_market_states_for_account(alice, [market])[0]

    health = market.health(alice, True)
    assert actual[4] == health
    assert abs(health - expected["health"]) / 1e18 < 1e-10

    bands_amm = amm.read_user_tick_numbers(alice)
    bands_views = views.get_market_amm_bands_for_account(alice, market)
    assert bands_amm == (bands_views[0]["band_num"], bands_views[-1]["band_num"])
    assert expected["bands"] == bands_amm
    assert len(bands_views) == bands_amm[1] - bands_amm[0] + 1
    assert sum(i["coll_balance"] for i in bands_views) == 50 * 10**18
    assert sum(i["debt_balance"] for i in bands_views) == 0

    coll_conversion_range = market.user_prices(alice)
    assert coll_conversion_range == (
        bands_views[0]["price_range"][1],
        bands_views[-1]["price_range"][0],
    )
    assert actual["coll_conversion_range"] == coll_conversion_range
    assert expected["coll_conversion_range"] == coll_conversion_range


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_adjust_loan_decrease_debt(views, market, hooks, amm, controller, alice, adjustment):
    controller.create_loan(alice, market, 50 * 10**18, 3000 * 10**18, 5, {"from": alice})
    hooks.set_response(adjustment, {"from": alice})

    expected = views.get_pending_market_state_for_account(alice, market, 0, -1000 * 10**18)

    assert expected["account_debt"] == 2000 * 10**18 + adjustment
    assert expected["amm_coll_balance"] == 50 * 10**18
    assert expected["amm_stable_balance"] == 0
    assert expected["hook_debt_adjustment"] == adjustment

    controller.adjust_loan(alice, market, 0, -1000 * 10**18, {"from": alice})

    # (market, account debt, amm coll balance, amm stable balance, health, bands, liquidation range)
    actual = views.get_market_states_for_account(alice, [market])[0]

    health = market.health(alice, True)
    assert actual[4] == health
    assert abs(health - expected["health"]) / 1e18 < 1e-10

    bands_amm = amm.read_user_tick_numbers(alice)
    bands_views = views.get_market_amm_bands_for_account(alice, market)
    assert bands_amm == (bands_views[0]["band_num"], bands_views[-1]["band_num"])
    assert expected["bands"] == bands_amm
    assert len(bands_views) == bands_amm[1] - bands_amm[0] + 1
    assert sum(i["coll_balance"] for i in bands_views) == 50 * 10**18
    assert sum(i["debt_balance"] for i in bands_views) == 0

    coll_conversion_range = market.user_prices(alice)
    assert coll_conversion_range == (
        bands_views[0]["price_range"][1],
        bands_views[-1]["price_range"][0],
    )
    assert actual["coll_conversion_range"] == coll_conversion_range
    assert expected["coll_conversion_range"] == coll_conversion_range


@pytest.mark.parametrize("adjustment", [-200 * 10**18, 0, 200 * 10**18])
def test_close_loan_simple(views, market, hooks, controller, alice, adjustment):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    hooks.set_response(adjustment, {"from": alice})

    expected = views.get_close_loan_amounts(alice, market)

    assert expected["total_debt_repaid"] == 1000 * 10**18
    assert expected["debt_burned"] == 1000 * 10**18 + adjustment
    assert expected["debt_from_amm"] == 0
    assert expected["coll_withdrawn"] == 50 * 10**18
    assert expected["hook_debt_adjustment"] == adjustment
