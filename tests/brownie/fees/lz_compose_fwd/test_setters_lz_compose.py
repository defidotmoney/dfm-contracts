import brownie
from brownie import ZERO_ADDRESS


def test_set_receiver(compose_fwd, deployer):
    compose_fwd.setRemoteReceiver(deployer, 42, {"from": deployer})
    assert compose_fwd.remoteReceiver() == deployer
    assert compose_fwd.remoteEid() == 42


def test_set_receiver_empty(compose_fwd, deployer):
    with brownie.reverts("DFM: Empty receiver"):
        compose_fwd.setRemoteReceiver(ZERO_ADDRESS, 42, {"from": deployer})


def test_set_receiver_unset_peer(compose_fwd, deployer):
    with brownie.reverts("DFM: Receiver peer unset"):
        compose_fwd.setRemoteReceiver(deployer, 888, {"from": deployer})


def test_set_receiver_onlyowner(compose_fwd, alice):
    with brownie.reverts("DFM: Only owner"):
        compose_fwd.setRemoteReceiver(alice, 42, {"from": alice})


def test_set_gas_limit(compose_fwd, deployer):
    compose_fwd.setGasLimit(12345678, {"from": deployer})
    assert compose_fwd.gasLimit() == 12345678


def test_set_gas_limit_too_low(compose_fwd, deployer):
    with brownie.reverts("DFM: gasLimit too low"):
        compose_fwd.setGasLimit(49999, {"from": deployer})

    compose_fwd.setGasLimit(50000, {"from": deployer})


def test_set_receiver_onlyowner(compose_fwd, alice):
    with brownie.reverts("DFM: Only owner"):
        compose_fwd.setGasLimit(12345678, {"from": alice})
