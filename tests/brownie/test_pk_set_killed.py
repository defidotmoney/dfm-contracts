import pytest
from brownie import chain


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


def test_set_killed_affects_max_provide(regulator, swap, pk, alice, deployer):
    swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)
    assert regulator.get_max_provide(pk) > 0
    assert regulator.get_max_withdraw(pk) == 0

    # 3 = kill both
    regulator.set_killed(3, {"from": deployer})
    assert regulator.get_max_provide(pk) == 0
    assert regulator.get_max_withdraw(pk) == 0

    # 2 = Kill withdraw only
    regulator.set_killed(2, {"from": deployer})
    assert regulator.get_max_provide(pk) > 0
    assert regulator.get_max_withdraw(pk) == 0

    # 1 = kill provide only
    regulator.set_killed(1, {"from": deployer})
    assert regulator.get_max_provide(pk) == 0
    assert regulator.get_max_withdraw(pk) == 0

    # 0 = kill none
    regulator.set_killed(0, {"from": deployer})
    assert regulator.get_max_provide(pk) > 0
    assert regulator.get_max_withdraw(pk) == 0


def test_set_killed_affects_max_withdraw(regulator, swap, pk, alice, deployer):
    swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)
    regulator.update(pk, {"from": alice})
    swap.exchange(1, 0, 3_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)
    assert regulator.get_max_provide(pk) == 0
    assert regulator.get_max_withdraw(pk) > 0

    # 3 = kill both
    regulator.set_killed(3, {"from": deployer})
    assert regulator.get_max_provide(pk) == 0
    assert regulator.get_max_withdraw(pk) == 0

    # 2 = Kill withdraw only
    regulator.set_killed(2, {"from": deployer})
    assert regulator.get_max_provide(pk) == 0
    assert regulator.get_max_withdraw(pk) == 0

    # 1 = kill provide only
    regulator.set_killed(1, {"from": deployer})
    assert regulator.get_max_provide(pk) == 0
    assert regulator.get_max_withdraw(pk) > 0

    # 0 = kill none
    regulator.set_killed(0, {"from": deployer})
    assert regulator.get_max_provide(pk) == 0
    assert regulator.get_max_withdraw(pk) > 0
