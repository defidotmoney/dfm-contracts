import brownie
from brownie import chain
import pytest


MAX_PK_DEBT = 100_000 * 10**18


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


def test_no_action_delay(regulator, swap, pk, alice, deployer):
    assert regulator.action_delay() == 0

    swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    regulator.update(pk, {"from": alice})

    swap.exchange(1, 0, 3_000_000 * 10**18, 0, {"from": alice})
    assert regulator.estimate_caller_profit(pk) > 0
    regulator.update(pk, {"from": alice})


def test_action_delay(regulator, swap, pk, alice, deployer):
    regulator.set_action_delay(100, {"from": deployer})
    assert regulator.action_delay() == 100

    swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    regulator.update(pk, {"from": alice})
    swap.exchange(1, 0, 3_000_000 * 10**18, 0, {"from": alice})

    chain.sleep(90)
    assert regulator.estimate_caller_profit(pk) == 0
    with brownie.reverts("DFM:R Action delay still active"):
        regulator.update(pk, {"from": alice})

    chain.mine(timedelta=11)
    assert regulator.estimate_caller_profit(pk) > 0
    regulator.update(pk, {"from": alice})


def test_action_delay_multiple_pegkeepers(regulator, pk_swaps, peg_keepers, alice, deployer):
    regulator.set_action_delay(100, {"from": deployer})

    pk_swaps[0].exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    pk_swaps[1].exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})
    regulator.update(peg_keepers[0], {"from": alice})
    pk_swaps[0].exchange(1, 0, 3_000_000 * 10**18, 0, {"from": alice})

    with brownie.reverts("DFM:R Action delay still active"):
        regulator.update(peg_keepers[0], {"from": alice})

    # 2nd pegkeeper should still be able to update
    regulator.update(peg_keepers[1], {"from": alice})
