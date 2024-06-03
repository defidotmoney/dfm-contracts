import brownie
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, alice, bob, controller):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})


def test_initial_state(controller):
    assert controller.is_protocol_enabled()


def test_set_protocol_enabled(controller, alice, deployer, guardian):
    controller.set_protocol_enabled(False, {"from": deployer})
    assert not controller.is_protocol_enabled()

    controller.set_protocol_enabled(True, {"from": deployer})
    assert controller.is_protocol_enabled()

    controller.set_protocol_enabled(False, {"from": guardian})
    assert not controller.is_protocol_enabled()

    with brownie.reverts("DFM:C Guardian can only disable"):
        controller.set_protocol_enabled(True, {"from": guardian})

    for is_enabled in [True, False]:
        with brownie.reverts("DFM:C Not owner or guardian"):
            controller.set_protocol_enabled(is_enabled, {"from": alice})


def test_create_loan(market, deployer, controller, alice):
    controller.set_protocol_enabled(False, {"from": deployer})

    with brownie.reverts("DFM:C Protocol pause, close only"):
        controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})


def test_adjust_loan(market, deployer, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.set_protocol_enabled(False, {"from": deployer})

    with brownie.reverts("DFM:C Protocol pause, close only"):
        controller.adjust_loan(alice, market, 25 * 10**18, 0, {"from": alice})


def test_collect_fees(deployer, controller):
    controller.set_protocol_enabled(False, {"from": deployer})

    with brownie.reverts("DFM:C Protocol pause, close only"):
        controller.collect_fees([], {"from": deployer})


def test_close_loan(market, deployer, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.set_protocol_enabled(False, {"from": deployer})

    # can still close when disabled
    controller.close_loan(alice, market, {"from": alice})


def test_liquidate(market, deployer, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.set_protocol_enabled(False, {"from": deployer})

    # can still liquidate when disabled
    controller.liquidate(market, alice, 0, {"from": alice})
