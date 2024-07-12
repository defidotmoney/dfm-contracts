import pytest
import brownie
from brownie import ZERO_ADDRESS, chain, Fixed


@pytest.fixture(scope="module", autouse=True)
def setup(converter, stable, controller):
    stable.mint(converter, 100_000 * 10**18, {"from": controller})


def test_not_enabled(converter, alice, deployer):
    converter.setIsEnabled(False, {"from": deployer})
    with brownie.reverts("DFM: Actions are disabled"):
        converter.swapNativeForDebt(10**18, 0, {"from": alice, "value": 10**18})


@pytest.mark.parametrize("value", [10**18 + 1, 10**18 - 1, 0])
def test_incorrect_value(converter, alice, value):
    with brownie.reverts("DFM: msg.value != amountIn"):
        converter.swapNativeForDebt(10**18, 0, {"from": alice, "value": value})


def test_amount_out_zero_amount_in_too_small(converter, dummy_oracle, alice):
    dummy_oracle.set_price(10**10, {"from": alice})
    chain.mine(timedelta=86400 * 30)
    with brownie.reverts("DFM: Would receive 0"):
        converter.swapNativeForDebt(100000, 0, {"from": alice, "value": 100000})


def test_amount_out_zero_relay_has_balance(converter, mock_bridge_relay, alice, deployer):
    deployer.transfer(mock_bridge_relay, 10**10)
    with brownie.reverts("DFM: Would receive 0"):
        converter.swapNativeForDebt(10**18, 0, {"from": alice, "value": 10**18})


def test_amount_out_zero_relay_unset(core, converter, relay_key, alice, deployer):
    core.setAddress(relay_key, ZERO_ADDRESS, {"from": deployer})
    with brownie.reverts("DFM: Would receive 0"):
        converter.swapNativeForDebt(10**18, 0, {"from": alice, "value": 10**18})


def test_slippage(converter, alice):
    expected = converter.getSwapNativeForDebtAmountOut(10**18)
    with brownie.reverts("DFM: Slippage"):
        converter.swapNativeForDebt(10**18, expected + 1, {"from": alice, "value": 10**18})


def test_cannot_transfer_to_relay(core, converter, relay_key, alice, deployer):
    # `core` cannot receive ETH
    core.setAddress(relay_key, core, {"from": deployer})

    with brownie.reverts("DFM: Transfer to relay failed"):
        converter.swapNativeForDebt(10**18, 0, {"from": alice, "value": 10**18})


def test_insufficient_stablecoin_balance(converter, stable, alice, deployer):
    stable.transfer(deployer, stable.balanceOf(converter), {"from": converter})

    with brownie.reverts("ERC20: transfer amount exceeds balance"):
        converter.swapNativeForDebt(10**18, 0, {"from": alice, "value": 10**18})
