import pytest
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(share_price_setup):
    pass


def test_cooldown_assets(staker, stable, alice, to_shares, initial_total_assets):
    staker.deposit(10**21, alice, {"from": alice})

    tx = staker.cooldownAssets(10**18, {"from": alice})

    assert stable.balanceOf(alice) == 10**24 - 10**21
    assert stable.balanceOf(staker) == initial_total_assets + 10**21

    assert staker.balanceOf(alice) == to_shares(10**21) - to_shares(10**18) - 1
    assert staker.totalSupply() == to_shares(initial_total_assets + 10**21) - to_shares(10**18) - 1

    assert staker.totalAssets() == initial_total_assets + 10**21 - 10**18
    assert staker.totalStoredAssets() == initial_total_assets + 10**21 - 10**18
    assert staker.totalCooldownAssets() == 10**18

    assert staker.cooldowns(alice) == (10**18, tx.timestamp + 604800)


def test_cooldown_shares(staker, stable, alice, to_shares, to_assets, initial_total_assets):
    staker.deposit(10**21, alice, {"from": alice})
    assets_per_share = staker.totalAssets() // staker.totalSupply() + 1

    tx = staker.cooldownShares(10**18, {"from": alice})

    assert stable.balanceOf(alice) == 10**24 - 10**21
    assert stable.balanceOf(staker) == initial_total_assets + 10**21

    assert staker.balanceOf(alice) == to_shares(10**21) - 10**18
    assert staker.totalSupply() == to_shares(initial_total_assets + 10**21) - 10**18

    expected = initial_total_assets + 10**21 - to_assets(10**18)
    assert 0 <= expected - staker.totalAssets() <= assets_per_share
    assert 0 <= expected - staker.totalStoredAssets() <= assets_per_share
    assert 0 <= staker.totalCooldownAssets() - to_assets(10**18) <= assets_per_share

    assert staker.cooldowns(alice) == (staker.totalCooldownAssets(), tx.timestamp + 604800)


def test_unstake(staker, stable, alice, to_shares, initial_total_assets):
    staker.deposit(10**21, alice, {"from": alice})

    staker.cooldownAssets(10**18, {"from": alice})
    chain.sleep(604800)
    staker.unstake(alice, {"from": alice})

    assert stable.balanceOf(alice) == 10**24 - 10**21 + 10**18
    assert stable.balanceOf(staker) == initial_total_assets + 10**21 - 10**18

    assert staker.balanceOf(alice) == to_shares(10**21) - to_shares(10**18) - 1
    assert staker.totalSupply() == to_shares(initial_total_assets + 10**21) - to_shares(10**18) - 1

    assert staker.totalAssets() == initial_total_assets + 10**21 - 10**18
    assert staker.totalStoredAssets() == initial_total_assets + 10**21 - 10**18
    assert staker.totalCooldownAssets() == 0

    assert staker.cooldowns(alice) == (0, 0)
