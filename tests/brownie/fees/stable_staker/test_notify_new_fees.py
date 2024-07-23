import brownie
import pytest
from brownie import ZERO_ADDRESS, chain


@pytest.fixture(scope="module")
def gov_staker(mock_fee_receiver):
    return mock_fee_receiver


@pytest.fixture(scope="module", autouse=True)
def setup(stable, controller, staker, alice, fee_agg, gov_staker, deployer):
    for acct in [alice, fee_agg]:
        stable.mint(acct, 10**30, {"from": controller})
        stable.approve(staker, 2**256 - 1, {"from": acct})

    staker.setGovStaker(gov_staker, {"from": deployer})


@pytest.mark.parametrize("amount", [0, 10**20])
def test_calls_regulator(staker, stable, reward_regulator, fee_agg, amount):
    stable.transfer(staker, amount, {"from": fee_agg})
    tx = staker.notifyNewFees(amount, {"from": fee_agg})

    subcall = next(i for i in tx.subcalls if i["function"] == "getStakerRewardAmount(uint256)")
    assert subcall["from"] == staker
    assert subcall["to"] == reward_regulator
    assert subcall["inputs"]["amount"] == amount // 7


def test_notify_new_fees_always_starts_stream(staker, stable, alice, fee_agg):
    staker.deposit(10**18, alice, {"from": alice})
    amount = 10**18 // (604800 * 2) * (604800 * 2)

    stable.transfer(staker, amount, {"from": fee_agg})
    staker.notifyNewFees(amount, {"from": fee_agg})
    last_day = staker.lastDistributionDay()

    for i in range(3):
        period_finish = staker.periodFinish()
        chain.sleep(10000)
        stable.transfer(staker, amount, {"from": fee_agg})
        staker.notifyNewFees(amount, {"from": fee_agg})

        assert staker.periodFinish() > period_finish
        assert staker.lastDistributionDay() == last_day

    chain.sleep(86400 * 7 + 1)
    staker.mint(0, alice, {"from": alice})
    chain.mine(timedelta=86400 * 2 + 1)

    assert 0 < stable.balanceOf(staker) - staker.totalAssets() < 604800


def test_zero_reward_amount(staker, alice, fee_agg):
    staker.deposit(10**18, alice, {"from": alice})

    staker.notifyNewFees(0, {"from": fee_agg})
    assert staker.periodFinish() == chain[-1].timestamp + 86400 * 2
    assert staker.rewardsPerSecond() == 0

    chain.mine(timedelta=86400 * 2 + 1)

    staker.mint(0, alice, {"from": alice})
    assert staker.convertToShares(10**18) == 10**18


def test_transfers_to_gov_staker(staker, stable, fee_agg, mock_stable_oracle, deployer, gov_staker):
    amount = 10**18

    # this makes the reward regulator split 20/80 between staker / gov_staker
    mock_stable_oracle.set_price(992 * 10**15, {"from": deployer})

    stable.transfer(staker, amount, {"from": fee_agg})
    staker.notifyNewFees(amount, {"from": fee_agg})
    chain.sleep(86400 * 7)
    staker.mint(0, deployer, {"from": deployer})

    assert stable.balanceOf(gov_staker) == amount // 5 * 4


def test_msg_value_refunded(staker, alice, fee_agg):
    alice.transfer(fee_agg, "1 ether")
    assert fee_agg.balance() == 10**18

    staker.notifyNewFees(0, {"from": fee_agg, "value": "1 ether"})
    assert fee_agg.balance() == 10**18


def test_revert_on_unset_gov_staker_when_pct(staker, stable, fee_agg, mock_stable_oracle, deployer):
    amount = 10**18
    stable.transfer(staker, amount, {"from": fee_agg})
    staker.setGovStaker(ZERO_ADDRESS, {"from": deployer})

    mock_stable_oracle.set_price(992 * 10**15, {"from": deployer})
    with brownie.reverts("ERC20: transfer to the zero address"):
        staker.notifyNewFees(amount, {"from": fee_agg})

    mock_stable_oracle.set_price(10**18, {"from": deployer})
    staker.notifyNewFees(amount, {"from": fee_agg})


def test_revert_on_unset_regulator(staker, stable, fee_agg, mock_stable_oracle, deployer):
    amount = 10**18
    stable.transfer(staker, amount, {"from": fee_agg})
    staker.setGovStaker(ZERO_ADDRESS, {"from": deployer})

    mock_stable_oracle.set_price(992 * 10**15, {"from": deployer})
    with brownie.reverts("ERC20: transfer to the zero address"):
        staker.notifyNewFees(amount, {"from": fee_agg})

    mock_stable_oracle.set_price(10**18, {"from": deployer})
    staker.notifyNewFees(amount, {"from": fee_agg})


def test_notify_onlyowner(staker, alice):
    with brownie.reverts():
        staker.notifyNewFees(0, {"from": alice})


def test_refund_reverts(staker, deployer, eth_receive_reverter):
    staker.setFeeAggregator(eth_receive_reverter, {"from": deployer})

    with brownie.reverts("DFM: Gas refund transfer failed"):
        staker.notifyNewFees(0, {"from": eth_receive_reverter, "value": "1 ether"})
