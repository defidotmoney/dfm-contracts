import pytest
import brownie
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(stable, controller, staker, alice, bob):
    for acct in [alice, bob]:
        stable.mint(acct, 10**20, {"from": controller})
        stable.approve(staker, 2**256 - 1, {"from": acct})
        staker.deposit(10**20, acct, {"from": acct})


def test_assumptions(staker):
    assert staker.cooldownDuration() == 604800
    assert staker.totalSupply() == 2 * 10**20
    assert staker.totalAssets() == 2 * 10**20
    assert staker.totalStoredAssets() == 2 * 10**20
    assert staker.totalCooldownAssets() == 0


@pytest.mark.parametrize("action", ["Assets", "Shares"])
def test_cooldown_single(staker, alice, action):
    tx = getattr(staker, f"cooldown{action}")(10**18, {"from": alice})

    assert staker.totalSupply() == 2 * 10**20 - 10**18
    assert staker.totalAssets() == 2 * 10**20 - 10**18
    assert staker.totalStoredAssets() == 2 * 10**20 - 10**18
    assert staker.totalCooldownAssets() == 10**18

    assert staker.balanceOf(alice) == 10**20 - 10**18
    assert staker.cooldowns(alice) == (10**18, tx.timestamp + 604800)


@pytest.mark.parametrize("action1", ["Assets", "Shares"])
@pytest.mark.parametrize("action2", ["Assets", "Shares"])
def test_cooldown_multiple_same_account(staker, alice, action1, action2):
    getattr(staker, f"cooldown{action1}")(10**18, {"from": alice})
    chain.sleep(12345)
    tx = getattr(staker, f"cooldown{action2}")(4 * 10**18, {"from": alice})

    assert staker.totalSupply() == 2 * 10**20 - 5 * 10**18
    assert staker.totalAssets() == 2 * 10**20 - 5 * 10**18
    assert staker.totalStoredAssets() == 2 * 10**20 - 5 * 10**18
    assert staker.totalCooldownAssets() == 5 * 10**18

    assert staker.balanceOf(alice) == 10**20 - 5 * 10**18
    assert staker.cooldowns(alice) == (5 * 10**18, tx.timestamp + 604800)


@pytest.mark.parametrize("action1", ["Assets", "Shares"])
@pytest.mark.parametrize("action2", ["Assets", "Shares"])
def test_cooldown_multiple_different_acounts(staker, alice, bob, action1, action2):
    tx1 = getattr(staker, f"cooldown{action1}")(10**18, {"from": alice})
    chain.sleep(12345)
    tx2 = getattr(staker, f"cooldown{action2}")(4 * 10**18, {"from": bob})

    assert staker.totalSupply() == 2 * 10**20 - 5 * 10**18
    assert staker.totalAssets() == 2 * 10**20 - 5 * 10**18
    assert staker.totalStoredAssets() == 2 * 10**20 - 5 * 10**18
    assert staker.totalCooldownAssets() == 5 * 10**18

    assert staker.balanceOf(alice) == 10**20 - 10**18
    assert staker.cooldowns(alice) == (10**18, tx1.timestamp + 604800)

    assert staker.balanceOf(bob) == 10**20 - 4 * 10**18
    assert staker.cooldowns(bob) == (4 * 10**18, tx2.timestamp + 604800)


@pytest.mark.parametrize("action1", ["Assets", "Shares"])
@pytest.mark.parametrize("action2", ["Assets", "Shares"])
def test_cooldown_many_multiple(staker, alice, bob, action1, action2):
    getattr(staker, f"cooldown{action1}")(10**18, {"from": alice})
    chain.sleep(12345)
    getattr(staker, f"cooldown{action2}")(2 * 10**18, {"from": bob})
    chain.sleep(12345)

    tx1 = getattr(staker, f"cooldown{action2}")(3 * 10**18, {"from": alice})
    chain.sleep(12345)
    tx2 = getattr(staker, f"cooldown{action1}")(4 * 10**18, {"from": bob})

    assert staker.totalSupply() == 2 * 10**20 - 10**19
    assert staker.totalAssets() == 2 * 10**20 - 10**19
    assert staker.totalStoredAssets() == 2 * 10**20 - 10**19
    assert staker.totalCooldownAssets() == 10**19

    assert staker.balanceOf(alice) == 10**20 - 4 * 10**18
    assert staker.cooldowns(alice) == (4 * 10**18, tx1.timestamp + 604800)

    assert staker.balanceOf(bob) == 10**20 - 6 * 10**18
    assert staker.cooldowns(bob) == (6 * 10**18, tx2.timestamp + 604800)


@pytest.mark.parametrize("amount", [10**18, 10**20])
def test_unstake_single(staker, stable, alice, amount):
    staker.cooldownAssets(amount, {"from": alice})

    chain.sleep(604800)
    staker.unstake(alice, {"from": alice})

    assert staker.totalSupply() == 2 * 10**20 - amount
    assert staker.totalAssets() == 2 * 10**20 - amount
    assert staker.totalStoredAssets() == 2 * 10**20 - amount
    assert staker.totalCooldownAssets() == 0

    assert stable.balanceOf(alice) == amount
    assert staker.balanceOf(alice) == 10**20 - amount
    assert staker.cooldowns(alice) == (0, 0)


@pytest.mark.parametrize("amount1", [10**18, 10**20])
@pytest.mark.parametrize("amount2", [4 * 10**18, 10**20])
def test_unstake_multiple(staker, stable, alice, bob, amount1, amount2):
    staker.cooldownAssets(amount1, {"from": alice})
    staker.cooldownAssets(amount2, {"from": bob})

    chain.sleep(604800)
    staker.unstake(alice, {"from": alice})
    staker.unstake(bob, {"from": bob})

    assert staker.totalSupply() == 2 * 10**20 - amount1 - amount2
    assert staker.totalAssets() == 2 * 10**20 - amount1 - amount2
    assert staker.totalStoredAssets() == 2 * 10**20 - amount1 - amount2
    assert staker.totalCooldownAssets() == 0

    assert stable.balanceOf(alice) == amount1
    assert staker.balanceOf(alice) == 10**20 - amount1
    assert staker.cooldowns(alice) == (0, 0)

    assert stable.balanceOf(bob) == amount2
    assert staker.balanceOf(bob) == 10**20 - amount2
    assert staker.cooldowns(bob) == (0, 0)


def test_unstake_different_receiver(staker, stable, alice, bob):
    staker.cooldownAssets(10**18, {"from": alice})

    chain.sleep(604800)
    staker.unstake(bob, {"from": alice})

    assert staker.totalSupply() == 2 * 10**20 - 10**18
    assert staker.totalAssets() == 2 * 10**20 - 10**18
    assert staker.totalStoredAssets() == 2 * 10**20 - 10**18
    assert staker.totalCooldownAssets() == 0

    assert stable.balanceOf(alice) == 0
    assert staker.balanceOf(alice) == 10**20 - 10**18
    assert staker.cooldowns(alice) == (0, 0)

    assert stable.balanceOf(bob) == 10**18
    assert staker.balanceOf(bob) == 10**20
    assert staker.cooldowns(bob) == (0, 0)


@pytest.mark.parametrize("action", ["Assets", "Shares"])
def test_cooldown_zero(staker, alice, action):
    with brownie.reverts("sMONEY: zero assets"):
        getattr(staker, f"cooldown{action}")(0, {"from": alice})


@pytest.mark.parametrize("action", ["Assets", "Shares"])
def test_cooldown_amount_exceeds_balance(staker, alice, action):
    with brownie.reverts(f"sMONEY: insufficient {action.lower()}"):
        getattr(staker, f"cooldown{action}")(10**20 + 1, {"from": alice})


def test_unstake_zero(staker, alice):
    with brownie.reverts("sMONEY: Nothing to withdraw"):
        staker.unstake(alice, {"from": alice})


def test_unstake_cooldown_still_active(staker, alice):
    staker.cooldownAssets(10**18, {"from": alice})
    chain.sleep(604800 - 10)
    with brownie.reverts("sMONEY: cooldown still active"):
        staker.unstake(alice, {"from": alice})

    chain.sleep(10)
    staker.unstake(alice, {"from": alice})
