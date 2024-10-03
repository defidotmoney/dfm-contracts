import itertools
import pytest

from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(stable, controller, fee_agg, mock_fee_receiver, bob, deployer):
    stable.mint(bob, 10**24, {"from": controller})
    stable.transfer(fee_agg, 10**24, {"from": bob})
    fee_agg.setFallbackReceiver(mock_fee_receiver, {"from": deployer})

    chain.mine(timedelta=604800)


@pytest.mark.parametrize("native_fee", [0, 10**12])
def test_fallback_receiver_only(fee_agg, stable, mock_fee_receiver, alice, native_fee):
    call_incentive = fee_agg.callerIncentive()
    assert call_incentive == 10**18

    initial_eth = alice.balance()
    mock_fee_receiver.setNativeFee(native_fee, {"from": alice})
    tx = fee_agg.processWeeklyDistribution({"from": alice, "value": native_fee})

    assert alice.balance() == initial_eth - native_fee
    assert stable.balanceOf(alice) == call_incentive
    assert stable.balanceOf(mock_fee_receiver) == 10**24 - call_incentive

    assert tx.events["Notified"]["amount"] == 10**24 - call_incentive


@pytest.mark.parametrize("cap", [0, 10**15])
def test_priority_receiver(
    fee_agg, stable, mock_fee_receiver, mock_fee_receiver2, alice, deployer, cap
):
    fee_agg.addPriorityReceivers([(mock_fee_receiver2, 1000, cap)], {"from": deployer})
    tx = fee_agg.processWeeklyDistribution({"from": alice})

    call_incentive = fee_agg.callerIncentive()
    total_distro = 10**24 - call_incentive
    priority_distro = cap or total_distro // 10

    assert stable.balanceOf(alice) == call_incentive
    assert stable.balanceOf(mock_fee_receiver2) == priority_distro
    assert stable.balanceOf(mock_fee_receiver) == total_distro - priority_distro

    assert tx.events["Notified"][0]["amount"] == priority_distro
    assert tx.events["Notified"][1]["amount"] == total_distro - priority_distro


def test_multiple_priority(fee_agg, stable, mock_fee_receiver, mock_fee_receiver2, alice, deployer):
    fee_agg.addPriorityReceivers(
        [
            (mock_fee_receiver2, 1000, 0),
            (mock_fee_receiver2, 5000, 10**18),
            (mock_fee_receiver2, 75, 0),
        ],
        {"from": deployer},
    )
    fee_agg.processWeeklyDistribution({"from": alice})

    call_incentive = fee_agg.callerIncentive()
    total_distro = 10**24 - call_incentive
    priority_distro = 10**18 + (total_distro * 1075 // 10000)

    assert stable.balanceOf(alice) == call_incentive
    assert stable.balanceOf(mock_fee_receiver2) == priority_distro
    assert stable.balanceOf(mock_fee_receiver) == total_distro - priority_distro


def test_no_fallback_amount(
    fee_agg, stable, mock_fee_receiver, mock_fee_receiver2, alice, deployer
):
    fee_agg.addPriorityReceivers([(mock_fee_receiver2, 10000, 0)], {"from": deployer})
    tx = fee_agg.processWeeklyDistribution({"from": alice})

    call_incentive = fee_agg.callerIncentive()
    total_distro = 10**24 - call_incentive

    assert stable.balanceOf(alice) == call_incentive
    assert stable.balanceOf(mock_fee_receiver2) == total_distro
    assert stable.balanceOf(mock_fee_receiver) == 0

    assert len(tx.events["Notified"]) == 1
    assert tx.events["Notified"][0]["amount"] == total_distro


def test_priority_returns_tokens(
    fee_agg, stable, mock_fee_receiver, mock_fee_receiver2, alice, deployer
):
    mock_fee_receiver2.setReturnAmount(3 * 10**19, {"from": deployer})

    fee_agg.addPriorityReceivers([(mock_fee_receiver2, 1000, 0)], {"from": deployer})

    tx = fee_agg.processWeeklyDistribution({"from": alice})

    call_incentive = fee_agg.callerIncentive()
    total_distro = 10**24 - call_incentive
    priority_distro = (total_distro // 10) - 3 * 10**19

    assert stable.balanceOf(alice) == call_incentive
    assert stable.balanceOf(mock_fee_receiver2) == priority_distro
    assert stable.balanceOf(mock_fee_receiver) == total_distro - priority_distro

    assert tx.events["Notified"][0]["amount"] == priority_distro + 3 * 10**19
    assert tx.events["Notified"][1]["amount"] == total_distro - priority_distro


@pytest.mark.parametrize("native_fees", itertools.product((0, 10**12), (0, 2 * 10**12)))
@pytest.mark.parametrize("excess_fee", [0, 10**13])
def test_gas_refund(
    fee_agg, mock_fee_receiver, mock_fee_receiver2, alice, deployer, native_fees, excess_fee
):
    mock_fee_receiver.setNativeFee(native_fees[0], {"from": deployer})
    mock_fee_receiver2.setNativeFee(native_fees[1], {"from": deployer})

    fee_agg.addPriorityReceivers([(mock_fee_receiver2, 1000, 0)], {"from": deployer})
    assert fee_agg.quoteProcessWeeklyDistribution() == sum(native_fees)

    initial_eth = alice.balance()
    fee_agg.processWeeklyDistribution({"from": alice, "value": sum(native_fees) + excess_fee})
    assert alice.balance() == initial_eth - sum(native_fees)


def test_set_caller_incentive(fee_agg, stable, alice, bob, deployer):
    stable.transfer(bob, 10**22, {"from": fee_agg})
    fee_agg.setCallerIncentive(0, {"from": deployer})
    fee_agg.processWeeklyDistribution({"from": alice})

    assert stable.balanceOf(alice) == 0

    chain.mine(timedelta=604800)
    fee_agg.setCallerIncentive(10**20, {"from": deployer})
    stable.transfer(fee_agg, 10**22, {"from": bob})
    fee_agg.processWeeklyDistribution({"from": alice})

    assert stable.balanceOf(alice) == 10**20
