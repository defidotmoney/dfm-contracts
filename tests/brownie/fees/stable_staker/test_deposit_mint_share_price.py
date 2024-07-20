import pytest


@pytest.fixture(scope="module", autouse=True)
def setup_mod(share_price_setup):
    pass


def test_initial_assumptions(staker, reward_amount, initial_total_assets, to_shares, to_assets):
    assert staker.totalSupply() == 10**18
    assert staker.totalAssets() == initial_total_assets == 10**18 + reward_amount
    assert staker.convertToShares(10**18) == 10**36 // (10**18 + reward_amount)
    assert staker.convertToAssets(10**18) == 10**18 + reward_amount
    assert staker.convertToShares(10**18) == to_shares(10**18)
    assert staker.convertToAssets(10**18) == to_assets(10**18)


def test_deposit(staker, stable, alice, to_shares, to_assets, initial_total_assets):
    staker.deposit(10**18, alice, {"from": alice})

    assert stable.balanceOf(alice) == 10**24 - 10**18
    assert stable.balanceOf(staker) == initial_total_assets + 10**18

    assert staker.balanceOf(alice) == to_shares(10**18)
    assert staker.totalSupply() == to_shares(initial_total_assets + 10**18)

    assert staker.convertToShares(10**18) == to_shares(10**18)
    assert (
        0
        <= 10**18 - staker.convertToAssets(to_shares(10**18))
        <= staker.totalAssets() // staker.totalSupply()
    )
    assert staker.totalAssets() == initial_total_assets + 10**18


def test_mint(staker, stable, alice, to_shares, to_assets, initial_total_assets):
    staker.mint(10**18, alice, {"from": alice})

    assert stable.balanceOf(alice) == 10**24 - to_assets(10**18)
    assert stable.balanceOf(staker) == initial_total_assets + to_assets(10**18)

    assert 0 <= 10**18 - staker.balanceOf(alice) <= 1
    assert staker.totalSupply() == 2 * 10**18

    assert staker.convertToShares(10**18) == to_shares(10**18)
    assert (
        0
        <= 10**18 - staker.convertToAssets(to_shares(10**18))
        <= staker.totalAssets() // staker.totalSupply() + 1
    )
    assert staker.totalAssets() == initial_total_assets + to_assets(10**18)


def test_multiple(staker, stable, alice, bob, to_shares, to_assets, initial_total_assets):
    staker.deposit(8 * 10**17, alice, {"from": alice})
    staker.mint(4 * 10**17, bob, {"from": bob})

    staker.mint(6 * 10**17, bob, {"from": bob})
    staker.deposit(2 * 10**17, alice, {"from": alice})

    assets_per_share = staker.totalAssets() // staker.totalSupply() + 1

    assert stable.balanceOf(alice) == 10**24 - 10**18
    assert 0 <= 10**24 - to_assets(10**18) - stable.balanceOf(bob) <= assets_per_share
    assert (
        0
        <= stable.balanceOf(staker) - initial_total_assets - 10**18 - to_assets(10**18)
        <= assets_per_share
    )

    assert 0 <= to_shares(10**18) - staker.balanceOf(alice) <= 1
    assert 0 <= 10**18 - staker.balanceOf(bob) <= 1
    assert (
        0
        <= to_shares(initial_total_assets + 10**18) + 10**18 - staker.totalSupply()
        <= assets_per_share
    )

    assert 0 <= to_shares(10**18) - staker.convertToShares(10**18) <= 2
    assert (
        0
        <= 10**18 - staker.convertToAssets(to_shares(10**18))
        <= staker.totalAssets() // staker.totalSupply()
    )
    assert (
        0
        <= staker.totalAssets() - initial_total_assets - 10**18 - to_assets(10**18)
        <= assets_per_share
    )
