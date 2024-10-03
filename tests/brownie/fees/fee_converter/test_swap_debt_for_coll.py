import pytest
from brownie import chain, Fixed


@pytest.fixture(scope="module", autouse=True)
def setup_base(alice, stable, controller):
    stable.mint(alice, 10**30, {"from": controller})


@pytest.fixture(scope="module", autouse=True)
def setup_parametrized(collateral, converter, alice, stable):
    collateral._mint_for_testing(converter, 10**30)
    stable.approve(converter, 2**256 - 1, {"from": alice})


@pytest.fixture(scope="module", autouse=True, params=[69420.42, 0.031337])
def price(request, dummy_oracle, deployer):
    value = int(Fixed(str(request.param)) * 10**18)
    dummy_oracle.set_price(value, {"from": deployer})
    chain.mine(timedelta=86400 * 30)
    return value


@pytest.mark.parametrize("min_out", [True, False])
@pytest.mark.parametrize("amount", [100_000, 422.817, 0.0808011])
def test_swap_debt_for_coll(
    FeeConverter, fee_agg, price, converter, stable, collateral, alice, amount, min_out
):
    amount_in = int(Fixed(str(amount)) * 10**36) // price
    expected_out = converter.getSwapDebtForCollAmountOut(collateral, amount_in)
    converter.swapDebtForColl(
        collateral, amount_in, expected_out if min_out else 0, {"from": alice}
    )

    assert stable.balanceOf(alice) == 10**30 - amount_in
    assert collateral.balanceOf(alice) == expected_out
    if converter in FeeConverter:
        assert stable.balanceOf(converter) == 0
        assert stable.balanceOf(fee_agg) == amount_in
    else:
        assert stable.balanceOf(converter) == amount_in
        assert stable.balanceOf(fee_agg) == 0
