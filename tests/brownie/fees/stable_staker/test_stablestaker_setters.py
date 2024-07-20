import pytest

import brownie
from brownie import ZERO_ADDRESS


@pytest.mark.parametrize("duration", [0, 604800 * 4, 86400])
def test_set_cooldown_duration(staker, deployer, duration):
    staker.setCooldownDuration(duration, {"from": deployer})
    assert staker.cooldownDuration() == duration


def test_set_fee_agg(staker, alice, deployer):
    for acct in [alice, ZERO_ADDRESS]:
        staker.setFeeAggregator(acct, {"from": deployer})
        assert staker.feeAggregator() == acct


def test_set_reward_reg(staker, alice, deployer):
    for acct in [alice, ZERO_ADDRESS]:
        staker.setRewardRegulator(acct, {"from": deployer})
        assert staker.rewardRegulator() == acct


def test_set_gov_staker(staker, alice, deployer):
    for acct in [alice, ZERO_ADDRESS]:
        staker.setGovStaker(acct, {"from": deployer})
        assert staker.govStaker() == acct


def test_set_cooldown_duration_max(staker, deployer):
    with brownie.reverts("sMONEY: Invalid duration"):
        staker.setCooldownDuration(604800 * 4 + 1, {"from": deployer})


def test_set_cooldown_duration_onlyowner(staker, alice):
    with brownie.reverts("DFM: Only owner"):
        staker.setCooldownDuration(12345, {"from": alice})


def test_set_fee_agg_onlyowner(staker, alice):
    with brownie.reverts("DFM: Only owner"):
        staker.setFeeAggregator(alice, {"from": alice})


def test_set_reward_reg_onlyowner(staker, alice):
    with brownie.reverts("DFM: Only owner"):
        staker.setRewardRegulator(alice, {"from": alice})


def test_set_gov_staker_onlyowner(staker, alice):
    with brownie.reverts("DFM: Only owner"):
        staker.setGovStaker(alice, {"from": alice})
