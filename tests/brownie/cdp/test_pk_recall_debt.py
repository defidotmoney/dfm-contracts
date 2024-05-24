import brownie
from brownie import chain
import pytest


MAX_PK_DEBT = 100_000 * 10**18


@pytest.fixture(scope="module")
def swap(pk_swaps):
    return pk_swaps[0]


@pytest.fixture(scope="module")
def coin(pk_swapcoins):
    return pk_swapcoins[0]


@pytest.fixture(scope="module", autouse=True)
def setup(regulator, peg_keepers, pk_swaps, pk_swapcoins, stable, alice, deployer):
    regulator.set_price_deviation(10**20, {"from": deployer})
    regulator.set_worst_price_threshold(10**16, {"from": deployer})

    for pk in peg_keepers:
        regulator.add_peg_keeper(pk, MAX_PK_DEBT, {"from": deployer})

    stable.mint(alice, 20_000_000 * 10**18, {"from": regulator})
    for swap, coin in zip(pk_swaps, pk_swapcoins):
        coin._mint_for_testing(alice, 6_000_000 * 10**18, {"from": alice})
        coin.approve(swap, 2**256 - 1, {"from": alice})
        stable.approve(swap, 2**256 - 1, {"from": alice})
        swap.add_liquidity([5_000_000 * 10**18] * 2, 0, {"from": alice})


def test_initial_assumptions(regulator, peg_keepers, stable):
    assert regulator.active_debt() == 0
    assert regulator.max_debt() == MAX_PK_DEBT * 3
    for pk in peg_keepers:
        assert pk.owed_debt() == 0
        assert pk.debt() == 0
        assert stable.balanceOf(pk) == MAX_PK_DEBT


def test_owed_debt_partial_repay(swap, regulator, pk, stable, alice, deployer):
    # buy `stable` using `coin`, increasing the price of stable so that the pegkeeper will deposit
    swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})

    # pk should not have >0 debt
    debt = pk.debt()
    assert 0 < debt < MAX_PK_DEBT
    assert debt + stable.balanceOf(pk) == MAX_PK_DEBT
    assert regulator.active_debt() == debt

    regulator.adjust_peg_keeper_debt_ceiling(pk, 0, {"from": deployer})

    # pk should now have 0 balance and >0 owed debt
    assert pk.debt() == debt
    assert pk.owed_debt() == debt
    assert stable.balanceOf(pk) == 0
    assert stable.balanceOf(regulator) == 0
    assert regulator.active_debt() == debt
    assert regulator.max_debt() == MAX_PK_DEBT * 2

    swap.exchange(1, 0, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})

    assert 0 < pk.debt() < debt
    assert pk.owed_debt() == pk.debt()
    assert stable.balanceOf(pk) == 0
    assert stable.balanceOf(regulator) == 0
    assert regulator.active_debt() == pk.debt()
    assert regulator.max_debt() == MAX_PK_DEBT * 2


def test_owed_debt_full_repay(swap, regulator, pk, stable, alice, deployer):
    swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})
    regulator.adjust_peg_keeper_debt_ceiling(pk, 0, {"from": deployer})
    swap.exchange(1, 0, 3_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})

    assert pk.debt() == 0
    assert pk.owed_debt() == 0
    assert stable.balanceOf(pk) == 0
    assert stable.balanceOf(regulator) == 0
    assert regulator.active_debt() == 0
    assert regulator.max_debt() == MAX_PK_DEBT * 2


def test_cannot_remove_with_owed_debt(swap, regulator, pk, peg_keepers, alice, deployer):
    swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})
    regulator.adjust_peg_keeper_debt_ceiling(pk, 0, {"from": deployer})
    swap.exchange(1, 0, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})

    with brownie.reverts("DFM:R keeper has debt"):
        regulator.remove_peg_keeper(pk, {"from": deployer})

    # we CAN remove a different peg keeper without debt
    regulator.remove_peg_keeper(peg_keepers[1], {"from": deployer})


def test_can_remove_after_owed_debt_settled(swap, regulator, pk, alice, deployer):
    swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})
    regulator.adjust_peg_keeper_debt_ceiling(pk, 0, {"from": deployer})
    swap.exchange(1, 0, 3_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})

    regulator.remove_peg_keeper(pk, {"from": deployer})


def test_increase_ceiling_with_owed_debt(swap, regulator, pk, stable, alice, deployer):
    swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})
    regulator.adjust_peg_keeper_debt_ceiling(pk, 0, {"from": deployer})
    swap.exchange(1, 0, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})
    debt = pk.owed_debt()
    assert debt > 0

    regulator.adjust_peg_keeper_debt_ceiling(pk, MAX_PK_DEBT, {"from": deployer})

    assert pk.owed_debt() == debt
    assert pk.debt() == debt
    assert stable.balanceOf(pk) == MAX_PK_DEBT
    assert regulator.active_debt() == debt

    swap.exchange(1, 0, 2_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(pk, {"from": alice})

    assert pk.debt() == 0
    assert pk.owed_debt() == 0
    assert stable.balanceOf(pk) == MAX_PK_DEBT
    assert regulator.active_debt() == 0
