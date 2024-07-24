import brownie
import itertools
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(votium_recv, deployer, alice, bob):
    votium_recv.setGauges([(alice, 0), (bob, 0)], {"from": deployer})


def test_initial_state(votium_recv, alice, bob):
    assert votium_recv.totalAllocationPoints() == 0
    assert votium_recv.getGaugeList() == []
    assert votium_recv.gaugeAllocationPoints(alice) == 0
    assert votium_recv.gaugeAllocationPoints(bob) == 0


def test_add_new_gauge(votium_recv, alice, deployer):
    votium_recv.setGauges([(alice, 25)], {"from": deployer})

    assert votium_recv.totalAllocationPoints() == 25
    assert votium_recv.getGaugeList() == [alice]
    assert votium_recv.gaugeAllocationPoints(alice) == 25


def test_increase_alloc(votium_recv, alice, deployer):
    votium_recv.setGauges([(alice, 25)], {"from": deployer})
    votium_recv.setGauges([(alice, 42)], {"from": deployer})

    assert votium_recv.totalAllocationPoints() == 42
    assert votium_recv.getGaugeList() == [alice]
    assert votium_recv.gaugeAllocationPoints(alice) == 42


def test_decrease_alloc(votium_recv, alice, deployer):
    votium_recv.setGauges([(alice, 25)], {"from": deployer})
    votium_recv.setGauges([(alice, 6)], {"from": deployer})

    assert votium_recv.totalAllocationPoints() == 6
    assert votium_recv.getGaugeList() == [alice]
    assert votium_recv.gaugeAllocationPoints(alice) == 6


def test_set_no_change(votium_recv, alice, deployer):
    votium_recv.setGauges([(alice, 25)], {"from": deployer})
    votium_recv.setGauges([(alice, 25)], {"from": deployer})

    assert votium_recv.totalAllocationPoints() == 25
    assert votium_recv.getGaugeList() == [alice]
    assert votium_recv.gaugeAllocationPoints(alice) == 25


def test_remove_gauge(votium_recv, alice, deployer):
    votium_recv.setGauges([(alice, 25)], {"from": deployer})
    votium_recv.setGauges([(alice, 0)], {"from": deployer})

    assert votium_recv.totalAllocationPoints() == 0
    assert votium_recv.getGaugeList() == []
    assert votium_recv.gaugeAllocationPoints(alice) == 0


def test_add_multiple(votium_recv, alice, bob, deployer):
    votium_recv.setGauges([(alice, 25)], {"from": deployer})
    votium_recv.setGauges([(bob, 42)], {"from": deployer})

    assert votium_recv.totalAllocationPoints() == 25 + 42
    assert votium_recv.getGaugeList() == [alice, bob]
    assert votium_recv.gaugeAllocationPoints(alice) == 25
    assert votium_recv.gaugeAllocationPoints(bob) == 42


@pytest.mark.parametrize("new_points", itertools.product((0, 6, 25, 77), (0, 33, 42, 101)))
def test_adjust_multiple(votium_recv, alice, bob, deployer, new_points):
    votium_recv.setGauges([(alice, 25)], {"from": deployer})
    votium_recv.setGauges([(bob, 42)], {"from": deployer})

    votium_recv.setGauges([(alice, new_points[0]), (bob, new_points[1])], {"from": deployer})

    assert votium_recv.totalAllocationPoints() == sum(new_points)
    assert votium_recv.getGaugeList() == [[alice, bob][i] for i in range(2) if new_points[i]]
    assert votium_recv.gaugeAllocationPoints(alice) == new_points[0]
    assert votium_recv.gaugeAllocationPoints(bob) == new_points[1]


@pytest.mark.parametrize("new_points", itertools.product((6, 25, 77), (0, 33, 101)))
def test_adjust_multiple_single_gauge_same_tx(votium_recv, alice, deployer, new_points):
    votium_recv.setGauges([(alice, new_points[0]), (alice, new_points[1])], {"from": deployer})

    assert votium_recv.totalAllocationPoints() == new_points[1]
    assert votium_recv.getGaugeList() == ([alice] if new_points[1] else [])
    assert votium_recv.gaugeAllocationPoints(alice) == new_points[1]


def test_cannot_remove_unset(votium_recv, alice, deployer):
    with brownie.reverts("DFM: cannot remove unset gauge"):
        votium_recv.setGauges([(alice, 0)], {"from": deployer})


def test_max_total_alloc(votium_recv, alice, bob, deployer):
    with brownie.reverts("DFM: MAX_TOTAL_ALLOCATION_POINTS"):
        votium_recv.setGauges([(alice, 10001)], {"from": deployer})

    with brownie.reverts("DFM: MAX_TOTAL_ALLOCATION_POINTS"):
        votium_recv.setGauges([(alice, 5000), (bob, 5001)], {"from": deployer})

    votium_recv.setGauges([(alice, 9000)], {"from": deployer})

    with brownie.reverts("DFM: MAX_TOTAL_ALLOCATION_POINTS"):
        votium_recv.setGauges([(bob, 1001)], {"from": deployer})


def test_onlyowner(votium_recv, alice):
    with brownie.reverts("DFM: Only owner"):
        votium_recv.setGauges([(alice, 20)], {"from": alice})
