import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(stable, controller, staker, alice, bob):
    for acct in [alice, bob]:
        stable.mint(acct, 10**24, {"from": controller})
        stable.approve(staker, 2**256 - 1, {"from": acct})


def test_initial_assumptions(staker):
    assert staker.convertToShares(10**18) == 10**18
    assert staker.convertToAssets(10**18) == 10**18


@pytest.mark.parametrize("action", ["deposit", "mint"])
def test_single(staker, stable, alice, action):
    getattr(staker, action)(10**18, alice, {"from": alice})

    assert stable.balanceOf(alice) == 10**24 - 10**18
    assert stable.balanceOf(staker) == 10**18

    assert staker.balanceOf(alice) == 10**18
    assert staker.totalSupply() == 10**18

    assert staker.convertToShares(10**18) == 10**18
    assert staker.convertToAssets(10**18) == 10**18
    assert staker.totalAssets() == 10**18


@pytest.mark.parametrize("action1", ["deposit", "mint"])
@pytest.mark.parametrize("action2", ["deposit", "mint"])
def test_multiple(staker, stable, alice, bob, action1, action2):
    getattr(staker, action1)(10**18, alice, {"from": alice})
    getattr(staker, action2)(2 * 10**18, bob, {"from": bob})

    assert stable.balanceOf(alice) == 10**24 - 10**18
    assert stable.balanceOf(bob) == 10**24 - 2 * 10**18
    assert stable.balanceOf(staker) == 3 * 10**18

    assert staker.balanceOf(alice) == 10**18
    assert staker.balanceOf(bob) == 2 * 10**18
    assert staker.totalSupply() == 3 * 10**18

    assert staker.convertToShares(10**18) == 10**18
    assert staker.convertToAssets(10**18) == 10**18
    assert staker.totalAssets() == 3 * 10**18


@pytest.mark.parametrize("action", ["deposit", "mint"])
def test_different_receiver(staker, stable, alice, bob, action):
    getattr(staker, action)(10**18, alice, {"from": bob})

    assert stable.balanceOf(alice) == 10**24
    assert stable.balanceOf(bob) == 10**24 - 10**18
    assert stable.balanceOf(staker) == 10**18

    assert staker.balanceOf(alice) == 10**18
    assert staker.balanceOf(bob) == 0
    assert staker.totalSupply() == 10**18

    assert staker.convertToShares(10**18) == 10**18
    assert staker.convertToAssets(10**18) == 10**18
    assert staker.totalAssets() == 10**18


@pytest.mark.parametrize("action1", ["deposit", "mint"])
@pytest.mark.parametrize("action2", ["deposit", "mint"])
def test_many_multiple(staker, stable, alice, bob, action1, action2):
    getattr(staker, action1)(2 * 10**17, alice, {"from": alice})
    getattr(staker, action2)(10**18, bob, {"from": bob})

    getattr(staker, action2)(7 * 10**17, alice, {"from": alice})
    getattr(staker, action1)(10**18, bob, {"from": bob})

    getattr(staker, action1)(10**18, bob, {"from": alice})
    getattr(staker, action2)(10**17, alice, {"from": bob})

    assert stable.balanceOf(alice) == 10**24 - 19 * 10**17
    assert stable.balanceOf(bob) == 10**24 - 21 * 10**17
    assert stable.balanceOf(staker) == 4 * 10**18

    assert staker.balanceOf(alice) == 10**18
    assert staker.balanceOf(bob) == 3 * 10**18
    assert staker.totalSupply() == 4 * 10**18

    assert staker.convertToShares(10**18) == 10**18
    assert staker.convertToAssets(10**18) == 10**18
    assert staker.totalAssets() == 4 * 10**18
