import pytest

import brownie

OPTS = "0x0003010011010000000000000000000000000000ea6001001303000000000000000000000000000000013880"


def test_assumptions(compose_fwd, stable, alice, bob):
    assert compose_fwd.feeAggregator() == alice
    assert compose_fwd.remoteReceiver() == bob
    assert compose_fwd.remoteEid() == 31337
    assert compose_fwd.gasLimit() == 80000
    assert compose_fwd.bridgeEpochFrequency() == 1
    assert compose_fwd.quoteNotifyNewFees(10**20) == 10**10
    assert stable.balanceOf(compose_fwd) == 10**24


def test_notify(compose_fwd, mock_endpoint, stable, alice):
    initial = alice.balance()
    tx = compose_fwd.notifyNewFees(10**24, {"from": alice, "value": 10**10})

    assert alice.balance() == initial - 10**10
    assert mock_endpoint.balance() == 10**10
    assert stable.balanceOf(compose_fwd) == 0

    event = tx.events["MessageSent"]
    assert event["options"] == OPTS
    assert event["dstEid"] == 31337


def test_gas_refund(compose_fwd, mock_endpoint, alice):
    initial = alice.balance()
    tx = compose_fwd.notifyNewFees(10**24, {"from": alice, "value": 3 * 10**10})

    assert alice.balance() == initial - 10**10
    assert mock_endpoint.balance() == 10**10


def test_below_min_amount(compose_fwd, stable, alice):
    stable.transfer(alice, stable.balanceOf(compose_fwd) - 10**18, {"from": compose_fwd})
    assert compose_fwd.quoteNotifyNewFees(10**18) == 0

    compose_fwd.notifyNewFees(10**24 - 10**18, {"from": alice})

    assert stable.balanceOf(compose_fwd) == 10**18


def test_msgvalue_too_small(compose_fwd, alice):
    with brownie.reverts("LzEndpointMock: Insufficient fee"):
        compose_fwd.notifyNewFees(10**24, {"from": alice, "value": 10**10 - 1})


def test_gas_refund_endpoint_reverts(
    LzComposeForwarder, core, stable, controller, eth_receive_reverter, deployer
):
    contract = LzComposeForwarder.deploy(
        core, stable, eth_receive_reverter, deployer, 31337, 80000, 1, {"from": deployer}
    )
    stable.mint(contract, 10**20, {"from": controller})

    with brownie.reverts("LzEndpointMock: Gas refund transfer failed"):
        contract.notifyNewFees(10**24, {"from": eth_receive_reverter, "value": 10**10 + 1})

    contract.notifyNewFees(10**24, {"from": eth_receive_reverter, "value": 10**10})


def test_gas_refund_fwd_reverts(LzComposeForwarder, core, stable, eth_receive_reverter, deployer):
    contract = LzComposeForwarder.deploy(
        core, stable, eth_receive_reverter, deployer, 31337, 80000, 1, {"from": deployer}
    )
    with brownie.reverts("DFM: Gas refund transfer failed"):
        contract.notifyNewFees(10**24, {"from": eth_receive_reverter, "value": 10**10})

    contract.notifyNewFees(10**24, {"from": eth_receive_reverter, "value": 0})
