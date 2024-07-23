import pytest

import brownie
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(stable, controller, fee_agg, mock_fee_receiver, bob, deployer):
    stable.mint(bob, 10**24, {"from": controller})
    fee_agg.setFallbackReceiver(mock_fee_receiver, {"from": deployer})


def test_same_week(fee_agg, stable, alice, bob):
    stable.transfer(fee_agg, 10**21, {"from": bob})
    fee_agg.processWeeklyDistribution({"from": alice})

    stable.transfer(fee_agg, 10**21, {"from": bob})
    with brownie.reverts("DFM: Already distro'd this week"):
        fee_agg.processWeeklyDistribution({"from": alice})

    chain.mine(timedelta=604800)

    fee_agg.processWeeklyDistribution({"from": alice})


def test_zero_amount(fee_agg, alice):
    with brownie.reverts("DFM: Nothing to distribute"):
        fee_agg.processWeeklyDistribution({"from": alice})


def test_amount_too_small(fee_agg, stable, alice, bob):
    stable.transfer(fee_agg, fee_agg.callerIncentive() * 2, {"from": bob})
    with brownie.reverts("DFM: Nothing to distribute"):
        fee_agg.processWeeklyDistribution({"from": alice})

    stable.transfer(fee_agg, 1, {"from": bob})
    fee_agg.processWeeklyDistribution({"from": alice})


def test_priority_receiver_bad_address(fee_agg, stable, mock_bridge_relay, alice, bob, deployer):
    stable.transfer(fee_agg, 10**24, {"from": bob})
    fee_agg.addPriorityReceivers([(mock_bridge_relay, 100, 0)], {"from": deployer})

    with brownie.reverts():
        fee_agg.processWeeklyDistribution({"from": alice})


def test_priority_receiver_notify_reverts(
    fee_agg, stable, mock_fee_receiver2, alice, bob, deployer
):
    mock_fee_receiver2.setRaiseOnNotify(True, {"from": deployer})

    stable.transfer(fee_agg, 10**24, {"from": bob})
    fee_agg.addPriorityReceivers([(mock_fee_receiver2, 100, 0)], {"from": deployer})

    with brownie.reverts("FeeReceiverMock: notifyNewFees"):
        fee_agg.processWeeklyDistribution({"from": alice})


@pytest.mark.parametrize("value", [0, 10**10 - 1])
def test_priority_receiver_msgvalue_too_smol(
    fee_agg, stable, mock_fee_receiver2, alice, bob, deployer, value
):
    mock_fee_receiver2.setNativeFee(10**10, {"from": deployer})

    stable.transfer(fee_agg, 10**24, {"from": bob})
    fee_agg.addPriorityReceivers([(mock_fee_receiver2, 100, 0)], {"from": deployer})

    with brownie.reverts("FeeReceiverMock: nativeFee"):
        fee_agg.processWeeklyDistribution({"from": alice, "value": value})


def test_fallback_receiver_bad_address(fee_agg, mock_bridge_relay, stable, alice, bob, deployer):
    fee_agg.setFallbackReceiver(mock_bridge_relay, {"from": deployer})

    stable.transfer(fee_agg, 10**24, {"from": bob})

    with brownie.reverts():
        fee_agg.processWeeklyDistribution({"from": alice})


def test_fallback_receiver_notify_reverts(fee_agg, stable, mock_fee_receiver, alice, bob, deployer):
    stable.transfer(fee_agg, 10**24, {"from": bob})
    mock_fee_receiver.setRaiseOnNotify(True, {"from": deployer})
    with brownie.reverts("FeeReceiverMock: notifyNewFees"):
        fee_agg.processWeeklyDistribution({"from": alice})


@pytest.mark.parametrize("value", [0, 10**10 - 1])
def test_fallback_receiver_msgvalue_too_smol(fee_agg, stable, mock_fee_receiver, alice, bob, value):

    mock_fee_receiver.setNativeFee(10**10, {"from": alice})

    stable.transfer(fee_agg, 10**24, {"from": bob})

    with brownie.reverts("FeeReceiverMock: nativeFee"):
        fee_agg.processWeeklyDistribution({"from": alice, "value": value})


def test_gas_refund_reverts(eth_receive_reverter, fee_agg, stable, bob):
    stable.transfer(fee_agg, 10**21, {"from": bob})
    with brownie.reverts("DFM: Gas refund transfer failed"):
        fee_agg.processWeeklyDistribution({"from": eth_receive_reverter, "value": 10**12})

    fee_agg.processWeeklyDistribution({"from": eth_receive_reverter})
