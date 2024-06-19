import brownie
import pytest
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(regulator, peg_keepers, pk_swaps, pk_swapcoins, stable, alice, deployer):
    for pk in peg_keepers:
        regulator.add_peg_keeper(pk, 10_000_000 * 10**18, {"from": deployer})

    stable.mint(alice, 20_000_000 * 10**18, {"from": regulator})
    for swap, coin in zip(pk_swaps, pk_swapcoins):
        coin._mint_for_testing(alice, 6_000_000 * 10**18, {"from": alice})
        coin.approve(swap, 2**256 - 1, {"from": alice})
        stable.approve(swap, 2**256 - 1, {"from": alice})
        swap.add_liquidity([5_000_000 * 10**18] * 2, 0, {"from": alice})
        swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})


def test_price_deviation_blocks(regulator, pk, alice, deployer):
    regulator.set_price_deviation(10**15, {"from": deployer})
    with brownie.reverts("DFM:PK Regulator ban"):
        regulator.update(pk, {"from": alice})


def test_high_price_deviation_disables_check(regulator, pk, alice, deployer):
    regulator.set_price_deviation(10**20, {"from": deployer})
    regulator.update(pk, {"from": alice})
