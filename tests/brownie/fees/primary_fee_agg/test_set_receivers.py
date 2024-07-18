import itertools
import pytest

import brownie
from brownie import ZERO_ADDRESS

# addPriorityReceivers
# removePriorityReceiver
# setFallbackReceiver


def test_initial_assumptions(fee_agg):
    assert fee_agg.priorityReceiverCount() == 0
    assert fee_agg.fallbackReceiver() == ZERO_ADDRESS
    assert fee_agg.lastDistributionWeek() == 0
    assert fee_agg.totalPriorityReceiverPct() == 0
    assert fee_agg.callerIncentive() == 10**18


def test_add_one(fee_agg, mock_fee_receiver, deployer):
    new_receiver = [(mock_fee_receiver, 100, 0)]
    fee_agg.addPriorityReceivers(new_receiver, {"from": deployer})

    assert fee_agg.priorityReceiverCount() == 1
    assert fee_agg.totalPriorityReceiverPct() == 100

    assert fee_agg.priorityReceivers(0) == new_receiver[0]


def test_add_many_one_call(fee_agg, mock_fee_receiver, alice, bob, deployer):
    new_receiver = [(mock_fee_receiver, 100, 0), (alice, 50, 10**20), (bob, 400, 10**24)]
    fee_agg.addPriorityReceivers(new_receiver, {"from": deployer})

    assert fee_agg.priorityReceiverCount() == 3
    assert fee_agg.totalPriorityReceiverPct() == 100 + 50 + 400

    for i in range(3):
        assert fee_agg.priorityReceivers(i) == new_receiver[i]


def test_add_many_multiple_calls(fee_agg, mock_fee_receiver, alice, bob, deployer):
    new_receiver = [(mock_fee_receiver, 100, 0), (alice, 50, 10**20), (bob, 400, 10**24)]
    for i in range(3):
        fee_agg.addPriorityReceivers([new_receiver[i]], {"from": deployer})

    assert fee_agg.priorityReceiverCount() == 3
    assert fee_agg.totalPriorityReceiverPct() == 100 + 50 + 400

    for i in range(3):
        assert fee_agg.priorityReceivers(i) == new_receiver[i]


def test_add_one_remove_one(fee_agg, mock_fee_receiver, deployer):
    new_receiver = [(mock_fee_receiver, 100, 0)]
    fee_agg.addPriorityReceivers(new_receiver, {"from": deployer})

    fee_agg.removePriorityReceiver(0, {"from": deployer})

    assert fee_agg.priorityReceiverCount() == 0
    assert fee_agg.totalPriorityReceiverPct() == 0

    with brownie.reverts():
        fee_agg.priorityReceivers(0)


@pytest.mark.parametrize("remove_idx", itertools.product([0, 1, 2], [0, 1], [0]))
def test_add_remove_complex(fee_agg, mock_fee_receiver, alice, bob, deployer, remove_idx):
    new_receiver = [(mock_fee_receiver, 100, 0), (alice, 50, 10**20), (bob, 400, 10**24)]
    fee_agg.addPriorityReceivers(new_receiver, {"from": deployer})

    for i in remove_idx:
        fee_agg.removePriorityReceiver(i, {"from": deployer})

        new_receiver[i] = new_receiver[-1]
        new_receiver.pop()

        assert fee_agg.priorityReceiverCount() == len(new_receiver)
        assert fee_agg.totalPriorityReceiverPct() == sum(i[1] for i in new_receiver)


def test_set_fallback_receiver(fee_agg, alice, deployer):
    fee_agg.setFallbackReceiver(alice, {"from": deployer})
    assert fee_agg.fallbackReceiver() == alice

    fee_agg.setFallbackReceiver(ZERO_ADDRESS, {"from": deployer})
    assert fee_agg.fallbackReceiver() == ZERO_ADDRESS


def test_priority_pct_too_high(fee_agg, alice, bob, deployer):
    new_receiver = [(alice, 5000, 10**20), (bob, 5000, 10**24), (deployer, 1000, 0)]
    with brownie.reverts("DFM: priority receiver pct > 100"):
        fee_agg.addPriorityReceivers(new_receiver, {"from": deployer})

    new_receiver = [(alice, 10001, 10**20)]
    with brownie.reverts("DFM: priority receiver pct > 100"):
        fee_agg.addPriorityReceivers(new_receiver, {"from": deployer})

    new_receiver = [(alice, 10000, 10**20)]
    fee_agg.addPriorityReceivers(new_receiver, {"from": deployer})

    new_receiver = [(alice, 1, 10**20)]
    with brownie.reverts("DFM: priority receiver pct > 100"):
        fee_agg.addPriorityReceivers(new_receiver, {"from": deployer})
