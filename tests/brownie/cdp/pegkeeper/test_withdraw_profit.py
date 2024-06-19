import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(regulator, peg_keepers, pk_swaps, pk_swapcoins, stable, alice, deployer):
    regulator.set_price_deviation(10**20, {"from": deployer})

    for pk in peg_keepers:
        regulator.add_peg_keeper(pk, 10_000_000 * 10**18, {"from": deployer})

    stable.mint(alice, 50_000_000 * 10**18, {"from": regulator})
    for swap, coin in zip(pk_swaps, pk_swapcoins):
        coin._mint_for_testing(alice, 10_000_000 * 10**18, {"from": alice})
        coin.approve(swap, 2**256 - 1, {"from": alice})
        stable.approve(swap, 2**256 - 1, {"from": alice})
        swap.add_liquidity([5_000_000 * 10**18] * 2, 0, {"from": alice})
        swap.exchange(0, 1, 1_000_000 * 10**18, 0, {"from": alice})


def test_withdraw_profit(regulator, pk, swap, coin, stable, alice, fee_receiver):
    regulator.update(pk, {"from": alice})

    swap.exchange(1, 0, 3_000_000 * 10**18, 0, {"from": alice})

    regulator.update(pk, {"from": alice})

    initial = swap.balanceOf(pk)
    profit = pk.calc_profit()
    expected = swap.remove_liquidity.call(profit, [0, 0], {"from": pk})
    assert profit > 10**18

    tx = regulator.withdraw_profit({"from": alice})

    assert "Profit" in tx.events
    assert swap.balanceOf(pk) + profit == initial
    assert coin.balanceOf(fee_receiver) == expected[0]
    assert stable.balanceOf(fee_receiver) == expected[1]


def test_withdraw_profit_many(regulator, peg_keepers, pk_swaps, coin, stable, alice, fee_receiver):
    for pk in peg_keepers:
        regulator.update(pk, {"from": alice})

    for swap in pk_swaps:
        swap.exchange(1, 0, 3_000_000 * 10**18, 0, {"from": alice})

    for pk in peg_keepers:
        regulator.update(pk, {"from": alice})

    tx = regulator.withdraw_profit({"from": alice})

    # use the events to check that the profit was withdrawn for each peg keeper
    assert len(tx.events["Profit"]) == len(peg_keepers)
    for pk, event in zip(peg_keepers, tx.events["Profit"]):
        assert event.address == pk


def test_no_profit_to_withdraw(regulator, pk, swap, coin, stable, alice, fee_receiver):
    regulator.update(pk, {"from": alice})
    swap.exchange(1, 0, 3_000_000 * 10**18, 0, {"from": alice})
    regulator.update(pk, {"from": alice})
    regulator.withdraw_profit({"from": alice})

    initial = swap.balanceOf(pk)
    profit = pk.calc_profit()
    assert profit == 0

    tx = regulator.withdraw_profit({"from": alice})
    assert "Profit" not in tx.events
    assert swap.balanceOf(pk) == initial


def test_profit_below_threshold(regulator, pk, swap, coin, stable, alice, fee_receiver):
    regulator.update(pk, {"from": alice})
    swap.exchange(1, 0, 3_000_000 * 10**18, 0, {"from": alice})
    regulator.update(pk, {"from": alice})

    regulator.withdraw_profit({"from": alice})

    # alice donates some profit to the pegkeeper, but not enough to pass the withdraw threshold
    swap.transfer(pk, 10**15, {"from": alice})

    initial = swap.balanceOf(pk)
    profit = pk.calc_profit()
    assert 0 < profit < 10**18

    tx = regulator.withdraw_profit({"from": alice})
    assert "Profit" not in tx.events
    assert swap.balanceOf(pk) == initial
