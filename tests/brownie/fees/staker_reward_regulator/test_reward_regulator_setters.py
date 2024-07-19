import pytest
import brownie


def test_initial_assumptions(reward_regulator):
    assert reward_regulator.minPrice() == 99 * 10**16
    assert reward_regulator.maxPrice() == 101 * 10**16
    assert reward_regulator.minStakerPct() == 3000
    assert reward_regulator.maxStakerPct() == 7000


@pytest.mark.parametrize(
    "min_price,max_price",
    [(9 * 10**17, 10**18), (10**18, 11 * 10**17), (98 * 10**16, 103 * 10**16), (10**18, 10**18)],
)
def test_set_price_bounds(reward_regulator, deployer, min_price, max_price):
    reward_regulator.setPriceBounds(min_price, max_price, {"from": deployer})

    assert reward_regulator.minPrice() == min_price
    assert reward_regulator.maxPrice() == max_price


@pytest.mark.parametrize(
    "min_pct,max_pct", [(2500, 4000), (0, 10000), (0, 0), (10000, 10000), (5000, 5000)]
)
def test_set_pct_bounds(reward_regulator, deployer, min_pct, max_pct):
    reward_regulator.setStakerPctBounds(min_pct, max_pct, {"from": deployer})

    assert reward_regulator.minStakerPct() == min_pct
    assert reward_regulator.maxStakerPct() == max_pct


def test_set_price_bounds_max_price_too_low(reward_regulator, deployer):
    with brownie.reverts("DFM: maxPrice below 1e18"):
        reward_regulator.setPriceBounds(99 * 10**16, 10**18 - 1, {"from": deployer})


def test_set_price_bounds_min_price_too_high(reward_regulator, deployer):
    with brownie.reverts("DFM: minPrice above 1e18"):
        reward_regulator.setPriceBounds(10**18 + 1, 101 * 10**16, {"from": deployer})


@pytest.mark.parametrize(
    "min_price,max_price",
    [(10**16, 10**18), (94 * 10**16, 104 * 10**16 + 1), (10**18, 10**19), (0, 2**256 - 1)],
)
def test_set_price_bounds_range_too_large(reward_regulator, deployer, min_price, max_price):
    with brownie.reverts("DFM: MAX_PRICE_RANGE"):
        reward_regulator.setPriceBounds(min_price, max_price, {"from": deployer})


def test_set_pct_bounds_max_too_high(reward_regulator, deployer):
    with brownie.reverts():
        reward_regulator.setStakerPctBounds(0, 10001, {"from": deployer})


def test_set_pct_bounds_min_too_high(reward_regulator, deployer):
    with brownie.reverts():
        reward_regulator.setStakerPctBounds(10001, 10000, {"from": deployer})


def test_set_pct_bounds_min_above_max(reward_regulator, deployer):
    with brownie.reverts():
        reward_regulator.setStakerPctBounds(5000, 4000, {"from": deployer})


def test_set_price_bounds_onlyowner(reward_regulator, alice):
    with brownie.reverts("DFM: Only owner"):
        reward_regulator.setPriceBounds(99 * 10**16, 101 * 10**16, {"from": alice})


def test_set_pct_bounds_onlyowner(reward_regulator, alice):
    with brownie.reverts("DFM: Only owner"):
        reward_regulator.setStakerPctBounds(3000, 7000, {"from": alice})
