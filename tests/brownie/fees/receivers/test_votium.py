import brownie
import pytest

from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(controller, stable, mock_endpoint):
    stable.mint(mock_endpoint, 10**24, {"from": controller})


def test_notify(stable, votium_recv, mock_endpoint, votium, alice, bob):
    stable.transfer(votium_recv, 10**24, {"from": mock_endpoint})
    tx = mock_endpoint.mockLzCompose(stable, bob, votium_recv, 10**24, {"from": alice})

    assert stable.balanceOf(votium) == 10**24
    assert stable.balanceOf(votium_recv) == 0

    assert tx.events["IncentivesAdded"]["gauges"] == [alice, bob]
    assert tx.events["IncentivesAdded"]["amounts"] == [3 * 10**23, 7 * 10**23]


def test_notify_multiple(stable, votium_recv, mock_endpoint, votium, alice, bob):
    stable.transfer(votium_recv, 10**22, {"from": mock_endpoint})
    mock_endpoint.mockLzCompose(stable, bob, votium_recv, 10**22, {"from": alice})

    stable.transfer(votium_recv, 10**22, {"from": mock_endpoint})
    tx = mock_endpoint.mockLzCompose(stable, bob, votium_recv, 10**22, {"from": alice})

    assert stable.balanceOf(votium) == 2 * 10**22
    assert stable.balanceOf(votium_recv) == 0

    assert tx.events["IncentivesAdded"]["gauges"] == [alice, bob]
    assert tx.events["IncentivesAdded"]["amounts"] == [3 * 10**21, 7 * 10**21]


def test_no_gauges(stable, votium_recv, mock_endpoint, votium, alice, bob, deployer):
    votium_recv.setGauges([(alice, 0), (bob, 0)], {"from": deployer})

    stable.transfer(votium_recv, 10**24, {"from": mock_endpoint})
    mock_endpoint.mockLzCompose(stable, bob, votium_recv, 10**24, {"from": alice})

    assert stable.balanceOf(votium) == 0
    assert stable.balanceOf(votium_recv) == 10**24


def test_min_total(stable, votium_recv, mock_endpoint, votium, alice, bob):
    amount = votium_recv.MIN_TOTAL_REWARD() - 1
    stable.transfer(votium_recv, amount, {"from": mock_endpoint})
    mock_endpoint.mockLzCompose(stable, bob, votium_recv, amount, {"from": alice})

    assert stable.balanceOf(votium) == 0
    assert stable.balanceOf(votium_recv) == amount

    stable.transfer(votium_recv, 1, {"from": mock_endpoint})
    mock_endpoint.mockLzCompose(stable, bob, votium_recv, amount, {"from": alice})

    assert stable.balanceOf(votium) == amount + 1
    assert stable.balanceOf(votium_recv) == 0


def test_only_endpoint(votium_recv, stable, alice):
    with brownie.reverts("DFM: Only lzEndpoint"):
        votium_recv.lzCompose(stable, 0, 0, ZERO_ADDRESS, 0, {"from": alice})


def test_incorrect_oapp(votium_recv, alice, bob, mock_endpoint):
    with brownie.reverts("DFM: Incorrect oApp"):
        mock_endpoint.mockLzCompose(alice, bob, votium_recv, 10**22, {"from": alice})


def test_incorrect_sender(votium_recv, stable, alice, mock_endpoint):
    with brownie.reverts("DFM: Incorrect remoteCaller"):
        mock_endpoint.mockLzCompose(stable, alice, votium_recv, 10**22, {"from": alice})
