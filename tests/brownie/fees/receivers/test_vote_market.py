import brownie
import pytest

from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(controller, stable, fee_agg):
    stable.mint(fee_agg, 10**24, {"from": controller})


def test_notify_create(stable, votemarket_recv, fee_agg, votemarket, alice, bob):
    stable.transfer(votemarket_recv, 10**24, {"from": fee_agg})
    tx = votemarket_recv.notifyNewFees(10**24, {"from": fee_agg})

    assert stable.balanceOf(votemarket) == 10**24
    assert stable.balanceOf(votemarket_recv) == 0

    assert "BountyCreated" in tx.events
    assert tx.events["BountyCreated"] == [
        {"gauge": alice, "bountyId": 0},
        {"gauge": bob, "bountyId": 1},
    ]
    assert len(tx.events["MockNewBounty"]) == 2


def test_notify_update(stable, votemarket_recv, fee_agg, votemarket):
    stable.transfer(votemarket_recv, 10**23, {"from": fee_agg})
    votemarket_recv.notifyNewFees(10**23, {"from": fee_agg})

    stable.transfer(votemarket_recv, 10**23, {"from": fee_agg})
    tx = votemarket_recv.notifyNewFees(10**23, {"from": fee_agg})

    assert stable.balanceOf(votemarket) == 2 * 10**23
    assert stable.balanceOf(votemarket_recv) == 0

    assert "BountyCreated" not in tx.events
    assert "MockNewBounty" not in tx.events
    assert len(tx.events["BountyRewardAdded"]) == 2


def test_notify_update_new_period(stable, votemarket_recv, fee_agg, votemarket, alice, bob):
    stable.transfer(votemarket_recv, 10**23, {"from": fee_agg})
    votemarket_recv.notifyNewFees(10**23, {"from": fee_agg})

    chain.mine(timedelta=604800 * 2)

    stable.transfer(votemarket_recv, 10**23, {"from": fee_agg})
    tx = votemarket_recv.notifyNewFees(10**23, {"from": fee_agg})

    assert stable.balanceOf(votemarket) == 2 * 10**23
    assert stable.balanceOf(votemarket_recv) == 0

    assert "BountyCreated" not in tx.events
    assert "MockNewBounty" not in tx.events
    assert len(tx.events["BountyRewardAdded"]) == 2


def test_notify_update_bounty_expired(stable, votemarket_recv, fee_agg, votemarket, alice, bob):
    stable.transfer(votemarket_recv, 10**23, {"from": fee_agg})
    votemarket_recv.notifyNewFees(10**23, {"from": fee_agg})

    chain.mine(timedelta=604800 * 6)

    stable.transfer(votemarket_recv, 10**23, {"from": fee_agg})
    tx = votemarket_recv.notifyNewFees(10**23, {"from": fee_agg})

    assert stable.balanceOf(votemarket) == 2 * 10**23
    assert stable.balanceOf(votemarket_recv) == 0

    assert "BountyCreated" in tx.events
    assert len(tx.events["MockNewBounty"]) == 2
    assert tx.events["BountyCreated"] == [
        {"gauge": alice, "bountyId": 2},
        {"gauge": bob, "bountyId": 3},
    ]


def test_no_gauges(votemarket_recv, votemarket, stable, fee_agg, alice, bob, deployer):
    votemarket_recv.setGauges([(alice, 0), (bob, 0)], {"from": deployer})

    stable.transfer(votemarket_recv, 10**24, {"from": fee_agg})
    votemarket_recv.notifyNewFees(10**24, {"from": fee_agg})

    assert stable.balanceOf(votemarket) == 0
    assert stable.balanceOf(votemarket_recv) == 10**24


def test_min_total(stable, votemarket_recv, fee_agg, votemarket):
    amount = votemarket_recv.MIN_TOTAL_REWARD() - 1

    stable.transfer(votemarket_recv, amount, {"from": fee_agg})
    votemarket_recv.notifyNewFees(amount, {"from": fee_agg})

    assert stable.balanceOf(votemarket) == 0
    assert stable.balanceOf(votemarket_recv) == amount

    stable.transfer(votemarket_recv, 1, {"from": fee_agg})
    votemarket_recv.notifyNewFees(1, {"from": fee_agg})

    assert stable.balanceOf(votemarket) == amount + 1
    assert stable.balanceOf(votemarket_recv) == 0


def test_exclusion_list(votemarket_recv, votemarket, fee_agg, stable, alice, bob, deployer):
    votemarket_recv.setExclusionList([alice, bob], True, {"from": deployer})

    stable.transfer(votemarket_recv, 10**24, {"from": fee_agg})
    tx = votemarket_recv.notifyNewFees(10**24, {"from": fee_agg})

    assert stable.balanceOf(votemarket) == 10**24
    assert stable.balanceOf(votemarket_recv) == 0

    assert len(tx.events["MockNewBounty"]) == 2
    assert tx.events["MockNewBounty"][0]["blacklist"] == [alice, bob]


def test_notify_only_fee_agg(votemarket_recv, alice):
    with brownie.reverts("DFM: Only feeAggregator"):
        votemarket_recv.notifyNewFees(0, {"from": alice})


def test_exclusion_onlyowner(votemarket_recv, alice):
    with brownie.reverts("DFM: Only owner"):
        votemarket_recv.setExclusionList([alice], False, {"from": alice})


def test_exclusion_double_add(votemarket_recv, alice, deployer):
    with brownie.reverts("DFM: Account already added"):
        votemarket_recv.setExclusionList([alice, alice], True, {"from": deployer})

    votemarket_recv.setExclusionList([alice], True, {"from": deployer})

    with brownie.reverts("DFM: Account already added"):
        votemarket_recv.setExclusionList([alice], True, {"from": deployer})


def test_exclusion_double_remove(votemarket_recv, alice, deployer):
    votemarket_recv.setExclusionList([alice], True, {"from": deployer})

    with brownie.reverts("DFM: Account not on list"):
        votemarket_recv.setExclusionList([alice, alice], False, {"from": deployer})

    votemarket_recv.setExclusionList([alice], False, {"from": deployer})

    with brownie.reverts("DFM: Account not on list"):
        votemarket_recv.setExclusionList([alice], False, {"from": deployer})
