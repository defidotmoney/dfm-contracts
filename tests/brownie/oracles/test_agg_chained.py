import pytest

import brownie
from brownie import ZERO_ADDRESS


def test_set_uptime_oracle_acl(chained_oracle, alice):
    with brownie.reverts("DFM: Only owner"):
        chained_oracle.setUptimeOracle(alice, {"from": alice})


def test_add_path_acl(chained_oracle, curve, alice):
    with brownie.reverts("DFM: Only owner"):
        chained_oracle.addCallPath(
            [(curve, 18, False, curve.price_oracle.encode_input(0))], {"from": alice}
        )


def test_remove_path_acl(chained_oracle, alice):
    with brownie.reverts("DFM: Only owner"):
        chained_oracle.removeCallPath(0, {"from": alice})


def test_reverts_before_setting_path(chained_oracle, deployer):
    with brownie.reverts("Division or modulo by zero"):
        chained_oracle.price_w({"from": deployer})


def test_reverts_decimals(chained_oracle, curve, deployer):
    curve.set_price(0, 10**18, {"from": deployer})
    with brownie.reverts("DFM: Maximum 18 decimals"):
        chained_oracle.addCallPath(
            [(curve, 19, False, curve.price_oracle.encode_input(0))], {"from": deployer}
        )

    with brownie.reverts("DFM: Decimals cannot be 0"):
        chained_oracle.addCallPath(
            [(curve, 0, False, curve.price_oracle.encode_input(0))], {"from": deployer}
        )


def test_reverts_oracle_returns_zero(chained_oracle, curve, deployer):
    with brownie.reverts("DFM: Oracle returned 0"):
        chained_oracle.addCallPath(
            [(curve, 18, False, curve.price_oracle.encode_input(0))], {"from": deployer}
        )

    curve.set_price(0, 10**18, {"from": deployer})
    chained_oracle.addCallPath(
        [(curve, 18, False, curve.price_oracle.encode_input(0))], {"from": deployer}
    )
    curve.set_price(0, 0, {"from": deployer})

    with brownie.reverts("DFM: Oracle returned 0"):
        chained_oracle.price()


def test_reverts_remove_final_call_path(chained_oracle, curve, deployer):
    curve.set_price(0, 10**18, {"from": deployer})
    chained_oracle.addCallPath(
        [(curve, 18, False, curve.price_oracle.encode_input(0))], {"from": deployer}
    )
    with brownie.reverts("DFM: Cannot remove only path"):
        chained_oracle.removeCallPath(0, {"from": deployer})


def test_reverts_remove_call_path_invalid_index(chained_oracle, curve, deployer):
    with brownie.reverts("DFM: Invalid path index"):
        chained_oracle.removeCallPath(0, {"from": deployer})

    curve.set_price(0, 10**18, {"from": deployer})
    chained_oracle.addCallPath(
        [(curve, 18, False, curve.price_oracle.encode_input(0))], {"from": deployer}
    )

    with brownie.reverts("DFM: Invalid path index"):
        chained_oracle.removeCallPath(1, {"from": deployer})


@pytest.mark.parametrize("idx", range(3))
def test_remove_path(chained_oracle, curve, curve2, curve3, deployer, idx):
    prices = [3000 * 10**18, 6 * 10**17, 69420 * 10**18]

    for c, price in zip([curve, curve2, curve3], prices):
        c.set_price(0, price, {"from": deployer})
        chained_oracle.addCallPath(
            [(c, 18, True, curve.price_oracle.encode_input(0))], {"from": deployer}
        )

    chained_oracle.removeCallPath(idx, {"from": deployer})
    del prices[idx]

    assert chained_oracle.price() == sum(prices) // 2


def test_set_uptime_oracle(chained_oracle, uptime_oracle, deployer):
    assert chained_oracle.uptimeOracle() == ZERO_ADDRESS

    chained_oracle.setUptimeOracle(uptime_oracle, {"from": deployer})

    assert chained_oracle.uptimeOracle() == uptime_oracle


def test_set_uptime_oracle_bad_status(chained_oracle, uptime_cl, uptime_oracle, deployer):
    uptime_cl.set_price(1, {"from": deployer})
    with brownie.reverts("DFM: Bad uptime answer"):
        chained_oracle.setUptimeOracle(uptime_oracle, {"from": deployer})


def test_uptime_use_stored_price(chained_oracle, curve, uptime_cl, uptime_oracle, deployer):
    old_price = 10**20
    new_price = 5 * 10**17

    chained_oracle.setUptimeOracle(uptime_oracle, {"from": deployer})
    curve.set_price(0, old_price, {"from": deployer})
    chained_oracle.addCallPath(
        [(curve, 18, True, curve.price_oracle.encode_input(0))], {"from": deployer}
    )

    # query the price as a write action to update stored price
    chained_oracle.price_w({"from": deployer})
    assert chained_oracle.storedPrice() == old_price

    # now the sequencer goes down and the curve oracle price drops significantly
    uptime_cl.set_price(1, {"from": deployer})
    curve.set_price(0, new_price, {"from": deployer})
    assert uptime_oracle.getUptimeStatus() is False

    # our oracle should continue to return the stored price
    assert chained_oracle.price() == old_price

    # directly calling the individual call path shows the new price
    assert chained_oracle.getCallPathResult(0) == new_price

    # nothing should change after a write update
    chained_oracle.price_w({"from": deployer})
    assert chained_oracle.storedPrice() == old_price
    assert chained_oracle.price() == old_price

    # the sequencer comes back online, prices should now update
    uptime_cl.set_price(0, {"from": deployer})

    assert chained_oracle.price() == new_price
    chained_oracle.price_w({"from": deployer})
    assert chained_oracle.storedPrice() == new_price
    assert chained_oracle.price() == new_price
