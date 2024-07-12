import pytest
from brownie import Fixed, chain


@pytest.fixture(scope="module", autouse=True, params=[69420.42, 0.031337])
def price(request, dummy_oracle, deployer):
    value = int(Fixed(str(request.param)) * 10**18)
    dummy_oracle.set_price(value, {"from": deployer})
    chain.mine(timedelta=86400 * 30)
    return value


def test_amount_out(price, converter, collateral):
    amount_out = converter.getSwapDebtForCollAmountOut(collateral, 5_000 * 10**18)
    assert amount_out == 5_000 * 10 ** (18 + collateral.decimals()) * 10100 // 10000 // price


def test_amount_out_max_bonus(price, converter, collateral):
    amount_out = converter.getSwapDebtForCollAmountOut(collateral, 14_000 * 10**18)
    adjusted_in = 14_000 * 10**18 + converter.maxSwapBonusAmount()
    assert amount_out == adjusted_in * 10 ** collateral.decimals() // price


def test_amount_in(converter, collateral):
    amount_out = converter.getSwapDebtForCollAmountOut(collateral, 5_000 * 10**18)
    amount_in = converter.getSwapDebtForCollAmountIn(collateral, amount_out)
    assert abs(converter.getSwapDebtForCollAmountOut(collateral, amount_in) - amount_out) < 100


def test_amount_in_max_bonus(converter, collateral):
    amount_out = converter.getSwapDebtForCollAmountOut(collateral, 50_000 * 10**18)
    amount_in = converter.getSwapDebtForCollAmountIn(collateral, amount_out)
    assert abs(converter.getSwapDebtForCollAmountOut(collateral, amount_in) - amount_out) < 100
