import pytest

import brownie

from brownie import chain, ZERO_ADDRESS


@pytest.mark.parametrize("price", [10**18, 10**20, 1234567890])
def test_simple_multiplication(chained_oracle, curve, deployer, price):
    curve.set_price(0, price, {"from": deployer})
    chained_oracle.addCallPath(
        [(curve, 18, True, curve.price_oracle.encode_input(0))], {"from": deployer}
    )

    assert chained_oracle.price() == price


@pytest.mark.parametrize("price", [10**18, 10**20, 1234567890])
def test_simple_division(chained_oracle, curve, price, deployer):
    curve.set_price(0, price, {"from": deployer})
    chained_oracle.addCallPath(
        [(curve, 18, False, curve.price_oracle.encode_input(0))], {"from": deployer}
    )

    assert chained_oracle.price() == 10**36 // price


def test_decimals(chained_oracle, curve, deployer):
    curve.set_price(0, 10**6, {"from": deployer})
    chained_oracle.addCallPath(
        [(curve, 11, True, curve.price_oracle.encode_input(0))], {"from": deployer}
    )

    assert chained_oracle.price() == 10 ** (6 + 18 - 11)


def test_multiple_paths(chained_oracle, curve, curve2, curve3, deployer):
    prices = [3000 * 10**18, 6 * 10**17, 69420 * 10**18]

    for c, price in zip([curve, curve2, curve3], prices):
        c.set_price(0, price, {"from": deployer})
        chained_oracle.addCallPath(
            [(c, 18, True, curve.price_oracle.encode_input(0))], {"from": deployer}
        )

    assert chained_oracle.price() == sum(prices) // 3


@pytest.mark.parametrize("price", [10**18, 3000 * 10**18, 5 * 10**16])
@pytest.mark.parametrize("price2", [6 * 10**17, 10**20, 69420 * 10**18])
@pytest.mark.parametrize("first_op", [True, False])
@pytest.mark.parametrize("second_op", [True, False])
def test_chained_call_path(
    chained_oracle, curve, uniswap, alice, bob, deployer, price, price2, first_op, second_op
):
    curve.set_price(0, price, {"from": deployer})
    uniswap.set_price(alice, bob, price2, {"from": deployer})

    chained_oracle.addCallPath(
        [
            (curve, 18, first_op, curve.price_oracle.encode_input(0)),
            (
                uniswap,
                18,
                second_op,
                uniswap.quoteAllAvailablePoolsWithTimePeriod.encode_input(10**18, alice, bob, 30),
            ),
        ]
    )

    assert chained_oracle.price() == chained_oracle.price_w.call()

    if first_op and second_op:
        assert chained_oracle.price() == price * price2 // 10**18
    elif first_op and (not second_op):
        assert chained_oracle.price() == 10**18 * price // price2
    elif (not first_op) and second_op:
        assert chained_oracle.price() == 10**36 // price * price2 // 10**18
    elif (not first_op) and (not second_op):
        assert chained_oracle.price() == 10**54 // price // price2
