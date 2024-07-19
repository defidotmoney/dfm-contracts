import pytest


@pytest.mark.parametrize("below_min", [0, 10**17])
@pytest.mark.parametrize("min_price", [10**18, 99 * 10**16])
@pytest.mark.parametrize("min_pct", [0, 3250, 10000])
def test_below_min_price(
    reward_regulator, mock_stable_oracle, deployer, min_price, min_pct, below_min
):
    mock_stable_oracle.set_price(min_price - below_min, {"from": deployer})
    reward_regulator.setPriceBounds(min_price, 101 * 10**16, {"from": deployer})
    reward_regulator.setStakerPctBounds(min_pct, 10000, {"from": deployer})
    assert reward_regulator.getStakerRewardAmount.call(10**18) == 10**18 * min_pct // 10000


@pytest.mark.parametrize("above_max", [0, 10**17])
@pytest.mark.parametrize("max_price", [10**18, 103 * 10**16])
@pytest.mark.parametrize("max_pct", [0, 6942, 10000])
def test_above_max_price(
    reward_regulator, mock_stable_oracle, deployer, max_price, max_pct, above_max
):
    mock_stable_oracle.set_price(max_price + above_max, {"from": deployer})
    reward_regulator.setPriceBounds(10**18, max_price, {"from": deployer})
    reward_regulator.setStakerPctBounds(0, max_pct, {"from": deployer})
    assert reward_regulator.getStakerRewardAmount.call(10**18) == 10**18 * max_pct // 10000


@pytest.mark.parametrize("price_bounds", [(990, 1010), (946, 1029), (1000, 1055), (975, 1000)])
@pytest.mark.parametrize("pct_bounds", [(0, 10000), (5010, 10000), (0, 4200), (2500, 9800)])
@pytest.mark.parametrize("price_pct", [0, 1, 0.5, 0.2274, 0.6942, 0.9999, 0.001])
def test_within_bounds(
    reward_regulator, mock_stable_oracle, deployer, price_bounds, pct_bounds, price_pct
):
    price_bounds = [i * 10**15 for i in price_bounds]
    bound_range = price_bounds[1] - price_bounds[0]
    price = price_bounds[0] + int(bound_range * price_pct)

    mock_stable_oracle.set_price(price, {"from": deployer})
    reward_regulator.setPriceBounds(price_bounds[0], price_bounds[1], {"from": deployer})
    reward_regulator.setStakerPctBounds(pct_bounds[0], pct_bounds[1], {"from": deployer})

    pct_range = pct_bounds[1] - pct_bounds[0]
    expected_pct = pct_bounds[0] + int(pct_range * price_pct)

    assert reward_regulator.getStakerRewardAmount.call(10**18) == 10**18 * expected_pct // 10000
