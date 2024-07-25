import pytest
from brownie import ZERO_ADDRESS, chain, Fixed


@pytest.fixture(scope="module", autouse=True, params=[3200, 25.8, 0.031337])
def price(request, dummy_oracle, deployer):
    value = int(Fixed(str(request.param)) * 10**18)
    dummy_oracle.set_price(value, {"from": deployer})
    chain.mine(timedelta=86400 * 30)
    return value


def test_initial_assumptions(controller, converter, mock_bridge_relay, core, weth, price):
    assert controller.get_oracle_price(weth) == price
    assert core.bridgeRelay() == mock_bridge_relay
    assert converter.relayMinBalance() == 10**10
    assert mock_bridge_relay.balance() == 0
    assert converter.canSwapNativeForDebt()


def test_no_swap_relay_has_balance(converter, mock_bridge_relay, deployer):
    deployer.transfer(mock_bridge_relay, 10**10)
    assert not converter.canSwapNativeForDebt()
    mock_bridge_relay.transfer(deployer, 1)
    assert converter.canSwapNativeForDebt()


def test_no_swap_relay_unset(core, converter, relay_key, deployer):
    core.setAddress(relay_key, ZERO_ADDRESS, {"from": deployer})
    assert not converter.canSwapNativeForDebt()


def test_amount_in(price, converter):
    amount_in = converter.getSwapNativeForDebtAmountIn(price)
    assert abs(amount_in - (10**18 * 10000 // 10100)) <= max(10**18 // price, 1)


def test_amount_in_max(price, converter):
    max_debt = converter.relayMaxSwapDebtAmount()
    amount_in = converter.getSwapNativeForDebtAmountIn(max_debt)
    assert abs(amount_in - (max_debt * 10**18 * 10000 // price // 10100)) <= (10**18 // price)


def test_amount_in_exceeds_max(converter):
    max_debt = converter.relayMaxSwapDebtAmount()
    assert converter.getSwapNativeForDebtAmountIn(max_debt + 1) == 0


def test_amount_out(price, converter):
    assert converter.getSwapNativeForDebtAmountOut(10**18) == price * 10100 // 10000


def test_amount_out_max(price, converter):
    max_debt = converter.relayMaxSwapDebtAmount()
    expected_in = (max_debt * 10**18 * 10000 // price // 10100) + max(10**18 // price, 1)
    amount_out = converter.getSwapNativeForDebtAmountOut(expected_in)
    assert max_debt - (price // 10**18 + 1) <= amount_out <= max_debt


def test_amount_out_exceeds_max(price, converter):
    max_debt = converter.relayMaxSwapDebtAmount()
    expected_in = (max_debt * 10**18 * 10000 // price // 10100) + max(10**18 // price, 1)
    assert converter.getSwapNativeForDebtAmountOut(expected_in + 1) == 0
