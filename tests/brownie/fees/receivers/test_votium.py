import brownie
import pytest

from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(controller, stable, mock_endpoint):
    stable.mint(mock_endpoint, 10**24, {"from": controller})


def test_notify(stable, votium_recv, mock_endpoint, votium, alice, bob):
    stable.transfer(votium_recv, 10**24, {"from": mock_endpoint})
    tx = votium_recv.lzCompose(stable, 0, 0, ZERO_ADDRESS, 0, {"from": mock_endpoint})

    assert stable.balanceOf(votium) == 10**24
    assert stable.balanceOf(votium_recv) == 0

    assert tx.events["IncentivesAdded"]["gauges"] == [alice, bob]
    assert tx.events["IncentivesAdded"]["amounts"] == [3 * 10**23, 7 * 10**23]


def test_notify_multiple(stable, votium_recv, mock_endpoint, votium, alice, bob):
    stable.transfer(votium_recv, 10**22, {"from": mock_endpoint})
    votium_recv.lzCompose(stable, 0, 0, ZERO_ADDRESS, 0, {"from": mock_endpoint})

    stable.transfer(votium_recv, 10**22, {"from": mock_endpoint})
    tx = votium_recv.lzCompose(stable, 0, 0, ZERO_ADDRESS, 0, {"from": mock_endpoint})

    assert stable.balanceOf(votium) == 2 * 10**22
    assert stable.balanceOf(votium_recv) == 0

    assert tx.events["IncentivesAdded"]["gauges"] == [alice, bob]
    assert tx.events["IncentivesAdded"]["amounts"] == [3 * 10**21, 7 * 10**21]


def test_no_gauges(stable, votium_recv, mock_endpoint, votium, alice, bob, deployer):
    votium_recv.setGauges([(alice, 0), (bob, 0)], {"from": deployer})

    stable.transfer(votium_recv, 10**24, {"from": mock_endpoint})
    votium_recv.lzCompose(stable, 0, 0, ZERO_ADDRESS, 0, {"from": mock_endpoint})

    assert stable.balanceOf(votium) == 0
    assert stable.balanceOf(votium_recv) == 10**24


def test_min_total(stable, votium_recv, mock_endpoint, votium):
    amount = votium_recv.MIN_TOTAL_REWARD() - 1
    stable.transfer(votium_recv, amount, {"from": mock_endpoint})
    votium_recv.lzCompose(stable, 0, 0, ZERO_ADDRESS, 0, {"from": mock_endpoint})

    assert stable.balanceOf(votium) == 0
    assert stable.balanceOf(votium_recv) == amount

    stable.transfer(votium_recv, 1, {"from": mock_endpoint})
    votium_recv.lzCompose(stable, 0, 0, ZERO_ADDRESS, 0, {"from": mock_endpoint})

    assert stable.balanceOf(votium) == amount + 1
    assert stable.balanceOf(votium_recv) == 0


def test_only_endpoint(votium_recv, stable, alice):
    with brownie.reverts("DFM: Only lzEndpoint"):
        votium_recv.lzCompose(stable, 0, 0, ZERO_ADDRESS, 0, {"from": alice})


def test_incorrect_oapp(votium_recv, alice, mock_endpoint):
    with brownie.reverts("DFM: Incorrect oApp"):
        votium_recv.lzCompose(alice, 0, 0, ZERO_ADDRESS, 0, {"from": mock_endpoint})
