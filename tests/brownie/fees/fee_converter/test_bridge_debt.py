import brownie
import pytest

from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup_base(bob, stable, controller, deployer):
    stable.mint(bob, 10**24, {"from": controller})
    stable.setPeer(31337, stable.address, {"from": deployer})


def test_bridge_debt(converter_bridge, mock_endpoint, stable, alice, bob):
    stable.transfer(converter_bridge, 10**18, {"from": bob})

    assert converter_bridge.getBridgeDebtReward() == 10**16
    assert converter_bridge.getBridgeDebtQuote() == 10**10

    initial = alice.balance()
    tx = converter_bridge.bridgeDebt({"from": alice, "value": 10**10})

    assert mock_endpoint.balance() == 10**10
    assert alice.balance() == initial - 10**10

    assert stable.balanceOf(converter_bridge) == 0
    assert stable.balanceOf(alice) == 10**16

    assert tx.events["MessageSent"]["dstEid"] == 31337
    assert tx.events["MessageSent"]["receiver"] == stable.address


def test_bridge_debt_max_bonus(converter_bridge, mock_endpoint, stable, alice, bob):
    stable.transfer(converter_bridge, 10**24, {"from": bob})

    assert converter_bridge.getBridgeDebtReward() == 10**18
    assert converter_bridge.getBridgeDebtQuote() == 10**10

    initial = alice.balance()
    tx = converter_bridge.bridgeDebt({"from": alice, "value": 10**10})

    assert mock_endpoint.balance() == 10**10
    assert alice.balance() == initial - 10**10

    assert stable.balanceOf(converter_bridge) == 0
    assert stable.balanceOf(alice) == 10**18

    assert tx.events["MessageSent"]["dstEid"] == 31337
    assert tx.events["MessageSent"]["receiver"] == stable.address


def test_bridge_debt_msgvalue_too_high(converter_bridge, mock_endpoint, stable, alice, bob):
    stable.transfer(converter_bridge, 10**24, {"from": bob})

    initial = alice.balance()
    tx = converter_bridge.bridgeDebt({"from": alice, "value": 10**18})

    assert mock_endpoint.balance() == 10**10
    assert alice.balance() == initial - 10**10

    assert stable.balanceOf(converter_bridge) == 0
    assert stable.balanceOf(alice) == 10**18

    assert tx.events["MessageSent"]["dstEid"] == 31337
    assert tx.events["MessageSent"]["receiver"] == stable.address


def test_bridge_debt_msgvalue_too_low(converter_bridge, stable, alice, bob):
    stable.transfer(converter_bridge, 10**24, {"from": bob})

    with brownie.reverts("LzEndpointMock: Insufficient fee"):
        converter_bridge.bridgeDebt({"from": alice, "value": 10**9})


def test_receiver_not_set(converter_bridge, stable, bob, deployer):
    stable.transfer(converter_bridge, 10**24, {"from": bob})
    converter_bridge.setPrimaryChainFeeAggregator(ZERO_ADDRESS, {"from": deployer})
    with brownie.reverts("DFM: Bridge receiver not set"):
        converter_bridge.bridgeDebt({"from": deployer, "value": 10**10})


def test_swap_native_for_debt(converter_bridge, core, stable, relay_key, bob, deployer):
    assert not converter_bridge.canSwapNativeForDebt()
    stable.transfer(converter_bridge, 10**24, {"from": bob})
    assert not converter_bridge.canSwapNativeForDebt()
    core.setAddress(relay_key, "0x0000000000000000000000000000000000000042", {"from": deployer})
    assert converter_bridge.canSwapNativeForDebt()

    with brownie.reverts("DFM: swapNativeForDebt first"):
        converter_bridge.bridgeDebt({"from": deployer, "value": 10**10})


def test_gas_refund_failed(converter_bridge, stable, eth_receive_reverter, bob):
    stable.transfer(converter_bridge, 10**24, {"from": bob})

    with brownie.reverts("DFM: Gas refund transfer failed"):
        converter_bridge.bridgeDebt({"from": eth_receive_reverter, "value": 10**18})
