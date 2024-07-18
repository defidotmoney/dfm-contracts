import pytest

import brownie
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(stable, controller, fee_agg, mock_fee_receiver, bob, deployer):
    stable.mint(bob, 10**24, {"from": controller})
    fee_agg.setFallbackReceiver(mock_fee_receiver, {"from": deployer})


def test_process_weekly_fallback_only(fee_agg, stable, mock_fee_receiver, alice, bob):
    call_incentive = fee_agg.callerIncentive()
    assert call_incentive == 10**18

    stable.transfer(fee_agg, 10**24, {"from": bob})
    tx = fee_agg.processWeeklyDistribution({"from": alice})

    assert stable.balanceOf(alice) == call_incentive
    assert stable.balanceOf(mock_fee_receiver) == 10**24 - call_incentive

    assert tx.events["Notified"]["amount"] == 10**24 - call_incentive


@pytest.mark.parametrize("cap", [0, 10**15])
def test_process_weekly_priority(
    fee_agg, stable, mock_fee_receiver, mock_fee_receiver2, alice, bob, deployer, cap
):

    fee_agg.addPriorityReceivers([(mock_fee_receiver2, 1000, cap)], {"from": deployer})

    stable.transfer(fee_agg, 10**24, {"from": bob})
    tx = fee_agg.processWeeklyDistribution({"from": alice})

    call_incentive = fee_agg.callerIncentive()
    total_distro = 10**24 - call_incentive
    priority_distro = cap or total_distro // 10

    assert stable.balanceOf(alice) == call_incentive
    assert stable.balanceOf(mock_fee_receiver2) == priority_distro
    assert stable.balanceOf(mock_fee_receiver) == total_distro - priority_distro

    assert tx.events["Notified"][0]["amount"] == priority_distro
    assert tx.events["Notified"][1]["amount"] == total_distro - priority_distro


def test_process_weekly_multiple_priority(
    fee_agg, stable, mock_fee_receiver, mock_fee_receiver2, alice, bob, deployer
):

    fee_agg.addPriorityReceivers(
        [
            (mock_fee_receiver2, 1000, 0),
            (mock_fee_receiver2, 5000, 10**18),
            (mock_fee_receiver2, 75, 0),
        ],
        {"from": deployer},
    )

    stable.transfer(fee_agg, 10**24, {"from": bob})
    tx = fee_agg.processWeeklyDistribution({"from": alice})

    call_incentive = fee_agg.callerIncentive()
    total_distro = 10**24 - call_incentive
    priority_distro = 10**18 + (total_distro * 1075 // 10000)

    assert stable.balanceOf(alice) == call_incentive
    assert stable.balanceOf(mock_fee_receiver2) == priority_distro
    assert stable.balanceOf(mock_fee_receiver) == total_distro - priority_distro


def test_process_weekly_no_fallback_amount(
    fee_agg, stable, mock_fee_receiver, mock_fee_receiver2, alice, bob, deployer
):

    fee_agg.addPriorityReceivers([(mock_fee_receiver2, 10000, 0)], {"from": deployer})

    stable.transfer(fee_agg, 10**24, {"from": bob})
    tx = fee_agg.processWeeklyDistribution({"from": alice})

    call_incentive = fee_agg.callerIncentive()
    total_distro = 10**24 - call_incentive

    assert stable.balanceOf(alice) == call_incentive
    assert stable.balanceOf(mock_fee_receiver2) == total_distro
    assert stable.balanceOf(mock_fee_receiver) == 0

    assert len(tx.events["Notified"]) == 1
    assert tx.events["Notified"][0]["amount"] == total_distro


def test_process_weekly_priority_returns_tokens(
    fee_agg, stable, mock_fee_receiver, mock_fee_receiver2, alice, bob, deployer
):

    fee_agg.addPriorityReceivers([(mock_fee_receiver2, 1000, 0)], {"from": deployer})
    mock_fee_receiver2.setReturnAmount(3 * 10**19, {"from": deployer})

    stable.transfer(fee_agg, 10**24, {"from": bob})
    tx = fee_agg.processWeeklyDistribution({"from": alice})

    call_incentive = fee_agg.callerIncentive()
    total_distro = 10**24 - call_incentive
    priority_distro = (total_distro // 10) - 3 * 10**19

    assert stable.balanceOf(alice) == call_incentive
    assert stable.balanceOf(mock_fee_receiver2) == priority_distro
    assert stable.balanceOf(mock_fee_receiver) == total_distro - priority_distro

    assert tx.events["Notified"][0]["amount"] == priority_distro + 3 * 10**19
    assert tx.events["Notified"][1]["amount"] == total_distro - priority_distro


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
    stable.transfer(fee_agg, 10**24, {"from": bob})
    fee_agg.addPriorityReceivers([(mock_fee_receiver2, 100, 0)], {"from": deployer})
    mock_fee_receiver2.setRaiseOnNotify(True, {"from": deployer})

    with brownie.reverts("FeeReceiverMock: notifyWeeklyFees"):
        fee_agg.processWeeklyDistribution({"from": alice})


def test_fallback_receiver_bad_address(fee_agg, mock_bridge_relay, stable, alice, bob, deployer):
    fee_agg.setFallbackReceiver(mock_bridge_relay, {"from": deployer})

    stable.transfer(fee_agg, 10**24, {"from": bob})

    with brownie.reverts():
        fee_agg.processWeeklyDistribution({"from": alice})


def test_fallback_receiver_notify_reverts(fee_agg, stable, mock_fee_receiver, alice, bob, deployer):
    stable.transfer(fee_agg, 10**24, {"from": bob})
    mock_fee_receiver.setRaiseOnNotify(True, {"from": deployer})
    with brownie.reverts("FeeReceiverMock: notifyWeeklyFees"):
        fee_agg.processWeeklyDistribution({"from": alice})


def test_set_caller_incentive(fee_agg, stable, alice, bob, deployer):
    stable.transfer(fee_agg, 10**20, {"from": bob})
    fee_agg.setCallerIncentive(0, {"from": deployer})
    fee_agg.processWeeklyDistribution({"from": alice})

    assert stable.balanceOf(alice) == 0

    chain.mine(timedelta=604800)
    fee_agg.setCallerIncentive(10**20, {"from": deployer})
    stable.transfer(fee_agg, 10**21, {"from": bob})
    fee_agg.processWeeklyDistribution({"from": alice})

    assert stable.balanceOf(alice) == 10**20
