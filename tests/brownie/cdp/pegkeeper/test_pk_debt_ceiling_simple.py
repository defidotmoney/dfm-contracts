import pytest


def test_add_peg_keeper(regulator, pk, stable, deployer):
    amount = 10_000 * 10**18
    regulator.add_peg_keeper(pk, amount, {"from": deployer})

    assert stable.totalSupply() == amount
    assert stable.balanceOf(pk) == amount
    assert pk.debt() == 0
    assert regulator.max_debt() == amount
    assert regulator.active_debt() == 0
    assert regulator.get_peg_keepers_with_debt_ceilings() == ([pk], [amount])


def test_add_multiple_peg_keepers(regulator, peg_keepers, stable, deployer):
    total = 0
    active_pk = []
    debt_ceilings = []
    for c, pk in enumerate(peg_keepers, start=1):
        amount = 10_000 * 10**18 * c
        regulator.add_peg_keeper(pk, amount, {"from": deployer})
        total += amount

        active_pk.append(pk)
        debt_ceilings.append(amount)

        assert stable.totalSupply() == total
        assert stable.balanceOf(pk) == amount
        assert pk.debt() == 0
        assert regulator.max_debt() == total
        assert regulator.active_debt() == 0
        assert regulator.get_peg_keepers_with_debt_ceilings() == (active_pk, debt_ceilings)


def test_remove_peg_keeper(regulator, pk, stable, deployer):
    amount = 10_000 * 10**18
    regulator.add_peg_keeper(pk, amount, {"from": deployer})
    regulator.remove_peg_keeper(pk, {"from": deployer})

    assert stable.totalSupply() == 0
    assert stable.balanceOf(pk) == 0
    assert pk.debt() == 0
    assert regulator.max_debt() == 0
    assert regulator.active_debt() == 0
    assert regulator.get_peg_keepers_with_debt_ceilings() == ([], [])


@pytest.mark.parametrize("offset", [0, 1, 2])
def test_remove_from_multiple(regulator, peg_keepers, stable, deployer, offset):
    active_pk = []
    debt_ceilings = []
    for c, pk in enumerate(peg_keepers, start=1):
        amount = 10_000 * 10**18 * c
        regulator.add_peg_keeper(pk, amount, {"from": deployer})

        active_pk.append(pk)
        debt_ceilings.append(amount)

    regulator.remove_peg_keeper(active_pk[offset], {"from": deployer})
    active_pk[offset] = active_pk[-1]
    del active_pk[-1]

    debt_ceilings[offset] = debt_ceilings[-1]
    del debt_ceilings[-1]

    assert stable.totalSupply() == sum(debt_ceilings)
    assert regulator.max_debt() == sum(debt_ceilings)
    assert regulator.active_debt() == 0
    assert regulator.get_peg_keepers_with_debt_ceilings() == (active_pk, debt_ceilings)


@pytest.mark.parametrize("adjustment", [0, 50_000 * 10**18, -4000 * 10**18])
def test_adjust_debt_ceiling(regulator, pk, stable, deployer, adjustment):
    amount = 10_000 * 10**18
    regulator.add_peg_keeper(pk, amount, {"from": deployer})

    amount += adjustment
    regulator.adjust_peg_keeper_debt_ceiling(pk, amount, {"from": deployer})

    assert stable.totalSupply() == amount
    assert stable.balanceOf(pk) == amount
    assert pk.debt() == 0
    assert regulator.max_debt() == amount
    assert regulator.active_debt() == 0
    assert regulator.get_peg_keepers_with_debt_ceilings() == ([pk], [amount])
