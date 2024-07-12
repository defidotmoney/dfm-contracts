import pytest
from brownie import chain, Fixed


@pytest.fixture(scope="module", autouse=True)
def setup(converter, stable, controller):
    stable.mint(converter, 100_000 * 10**18, {"from": controller})


@pytest.fixture(scope="module", autouse=True, params=[3200, 0.888])
def price(request, dummy_oracle, deployer):
    value = int(Fixed(str(request.param)) * 10**18)
    dummy_oracle.set_price(value, {"from": deployer})
    chain.mine(timedelta=86400 * 30)
    return value


@pytest.mark.parametrize("min_out", [True, False])
@pytest.mark.parametrize("amount", [4950, 422.817, 0.0808011])
def test_swap_native_for_debt(price, converter, stable, mock_bridge_relay, alice, amount, min_out):
    amount_in = int(Fixed(str(amount)) * 10**36) // price
    expected_out = converter.getSwapNativeForDebtAmountOut(amount_in)
    converter.swapNativeForDebt(
        amount_in,
        expected_out if min_out else 0,
        {"from": alice, "value": amount_in},
    )

    assert stable.balanceOf(alice) == expected_out
    assert mock_bridge_relay.balance() == amount_in
    assert converter.balance() == 0
