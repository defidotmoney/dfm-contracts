import pytest
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(stable, controller, staker, alice):
    stable.mint(alice, 10**24, {"from": controller})
    stable.approve(staker, 2**256 - 1, {"from": alice})
    staker.deposit(10**18, alice, {"from": alice})


def test_donation_does_not_affect_shares(staker, stable, alice):
    stable.transfer(staker, 10**18, {"from": alice})

    assert staker.convertToShares(10**18) == 10**18
    assert staker.convertToAssets(10**18) == 10**18
    assert staker.totalAssets() == 10**18


@pytest.mark.parametrize("action", ["deposit", "mint"])
def test_donation_with_deposit(staker, stable, alice, action):
    stable.transfer(staker, 10**18, {"from": alice})
    getattr(staker, action)(10**18, alice, {"from": alice})

    assert staker.convertToShares(10**18) == 10**18
    assert staker.convertToAssets(10**18) == 10**18
    assert staker.totalAssets() == 2 * 10**18


@pytest.mark.parametrize("action", ["Assets", "Shares"])
def test_donation_with_cooldown(staker, stable, alice, action):
    stable.transfer(staker, 10**18, {"from": alice})
    getattr(staker, f"cooldown{action}")(10**17, {"from": alice})

    assert staker.convertToShares(10**18) == 10**18
    assert staker.convertToAssets(10**18) == 10**18
    assert staker.totalAssets() == 9 * 10**17


@pytest.mark.parametrize("action", ["Assets", "Shares"])
def test_donation_with_unstake(staker, stable, alice, action):
    getattr(staker, f"cooldown{action}")(10**17, {"from": alice})
    stable.transfer(staker, 10**18, {"from": alice})
    chain.sleep(604800)
    staker.unstake(alice, {"from": alice})

    assert staker.convertToShares(10**18) == 10**18
    assert staker.convertToAssets(10**18) == 10**18
    assert staker.totalAssets() == 9 * 10**17
