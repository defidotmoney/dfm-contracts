import pytest

import brownie
from brownie import chain, ZERO_ADDRESS


@pytest.fixture(scope="module")
def agg(ChainlinkAggregatorMock, deployer):
    mock = ChainlinkAggregatorMock.deploy(0, 0, {"from": deployer})
    mock.set_updated_at(chain[-1].timestamp - 86400, {"from": deployer})

    return mock


@pytest.fixture(scope="module")
def uptime_oracle(Layer2UptimeOracle, agg, deployer):
    return Layer2UptimeOracle.deploy(agg, {"from": deployer})


@pytest.fixture(scope="module")
def l2_hook(L2SequencerUptimeHook, uptime_oracle, deployer):
    return L2SequencerUptimeHook.deploy(uptime_oracle, {"from": deployer})


@pytest.fixture(scope="module", autouse=True)
def setup(l2_hook, collateral, controller, alice, deployer):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})

    controller.add_market_hook(ZERO_ADDRESS, l2_hook, {"from": deployer})


def test_hook_config(l2_hook, controller):
    data = controller.get_market_hooks(ZERO_ADDRESS)
    assert data == [(l2_hook, 0, [True, True, False, False])]


def test_create_loan_sequencer_up(controller, market, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})


def test_adjust_loan_reduce_coll_sequencer_up(controller, market, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, -10 * 10**18, 0, {"from": alice})


def test_adjust_loan_increase_debt_sequencer_up(controller, market, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, 0, 100 * 10**18, {"from": alice})


def test_create_loan_sequencer_down(agg, controller, market, alice):
    agg.set_price(1, {"from": alice})
    with brownie.reverts("DFM: Sequencer down, no new loan"):
        controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})


def test_adjust_loan_reduce_coll_sequencer_down(agg, controller, market, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    agg.set_price(1, {"from": alice})
    with brownie.reverts("DFM: Sequencer down, no coll--"):
        controller.adjust_loan(alice, market, -10 * 10**18, 0, {"from": alice})


def test_adjust_loan_increase_debt_sequencer_down(agg, controller, market, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    agg.set_price(1, {"from": alice})

    with brownie.reverts("DFM: Sequencer down, no debt++"):
        controller.adjust_loan(alice, market, 0, 100 * 10**18, {"from": alice})


def test_increase_coll_and_reduce_debt_sequencer_down(agg, controller, market, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    agg.set_price(1, {"from": alice})

    # even with sequencer down, it should be allowed to perform these actions
    controller.adjust_loan(alice, market, 10 * 10**18, -100 * 10**18, {"from": alice})
