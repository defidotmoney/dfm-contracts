import brownie
from brownie import chain
import pytest


MAX_PK_DEBT = 100_000 * 10**18


@pytest.fixture(scope="module")
def regulator2(PegKeeperRegulator, core, stable, agg_stable, controller, deployer):
    contract = PegKeeperRegulator.deploy(core, stable, agg_stable, controller, {"from": deployer})
    stable.setMinter(contract, True, {"from": deployer})

    return contract


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


def test_migrate_pk_regulator(
    pk_swaps, regulator, regulator2, peg_keepers, alice, deployer, controller, stable
):
    pk_swaps[0].exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    pk_swaps[2].exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)

    regulator.update(peg_keepers[0], {"from": alice})
    regulator.update(peg_keepers[2], {"from": alice})

    regulator.adjust_peg_keeper_debt_ceiling(peg_keepers[0], 69420, {"from": deployer})

    pk_swaps[0].exchange(1, 0, 1_000_000 * 10**18, 0, {"from": alice})
    chain.mine(timedelta=86400)
    regulator.update(peg_keepers[0], {"from": alice})

    assert peg_keepers[0].owed_debt() > 0
    assert peg_keepers[2].debt() > 0

    controller.set_peg_keeper_regulator(regulator2, True, {"from": deployer})

    assert (
        regulator.get_peg_keepers_with_debt_ceilings()
        == regulator2.get_peg_keepers_with_debt_ceilings()
    )
    assert regulator.active_debt() == regulator2.active_debt()
    assert regulator.max_debt() == regulator2.max_debt()
    assert regulator.owed_debt() == regulator2.owed_debt()

    for pk in peg_keepers:
        assert pk.regulator() == regulator2

    with brownie.reverts("PegKeeper: Only regulator"):
        regulator.adjust_peg_keeper_debt_ceiling(
            peg_keepers[1], MAX_PK_DEBT * 2, {"from": deployer}
        )

    with brownie.reverts("PegKeeper: Only regulator"):
        regulator.adjust_peg_keeper_debt_ceiling(peg_keepers[1], 12345, {"from": deployer})

    regulator2.adjust_peg_keeper_debt_ceiling(peg_keepers[1], MAX_PK_DEBT * 2, {"from": deployer})
    assert stable.balanceOf(peg_keepers[1]) == MAX_PK_DEBT * 2
    regulator2.adjust_peg_keeper_debt_ceiling(peg_keepers[1], 12345, {"from": deployer})
    assert stable.balanceOf(peg_keepers[1]) == 12345
