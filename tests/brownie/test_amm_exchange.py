import brownie
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(collateral_list, stable, controller, market_list, amm_list, oracle, alice, deployer):

    for coll, amm, market in zip(collateral_list, amm_list, market_list):
        coll._mint_for_testing(deployer, 50 * 10**18)
        coll.approve(controller, 2**256 - 1, {"from": deployer})

        controller.create_loan(
            deployer, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": deployer}
        )

        stable.approve(amm, 2**256 - 1, {"from": alice})
        coll.approve(amm, 2**256 - 1, {"from": alice})

    oracle.set_price(500 * 10**18, {"from": deployer})
    stable.transfer(alice, 300_000 * 10**18, {"from": deployer})


@pytest.mark.parametrize("x,y", [(0, 0), (1, 1), (2, 0), (0, 2)])
def test_invalid_index(amm, alice, x, y):
    with brownie.reverts("DFM:A Wrong index"):
        amm.exchange(x, y, 1000 * 10**18, 0, {"from": alice})

    with brownie.reverts("DFM:A Wrong index"):
        amm.exchange_dy(x, y, 1000 * 10**18, 0, {"from": alice})


def test_exchange_erc20_returns_none(amm2, oracle, collateral2, alice):
    initial = collateral2.balanceOf(alice)
    amm2.exchange(0, 1, 1000 * 10**18, 0, {"from": alice})
    assert collateral2.balanceOf(alice) > initial

    oracle.set_price(5000 * 10**18, {"from": alice})
    initial = collateral2.balanceOf(alice)
    amm2.exchange(1, 0, initial, 0, {"from": alice})
    assert collateral2.balanceOf(alice) == 0


def test_exchange_erc20_returns_true_false(amm3, oracle, collateral3, alice):
    initial = collateral3.balanceOf(alice)
    amm3.exchange(0, 1, 1000 * 10**18, 0, {"from": alice})
    assert collateral3.balanceOf(alice) > initial

    oracle.set_price(5000 * 10**18, {"from": alice})
    initial = collateral3.balanceOf(alice)
    amm3.exchange(1, 0, initial, 0, {"from": alice})
    assert collateral3.balanceOf(alice) == 0


def test_insufficient_balance_erc20_returns_none(amm2, oracle, collateral2, alice):
    initial = collateral2.balanceOf(alice)
    amm2.exchange(0, 1, 1000 * 10**18, 0, {"from": alice})
    oracle.set_price(5000 * 10**18, {"from": alice})
    initial = collateral2.balanceOf(alice)
    with brownie.reverts():
        amm2.exchange(1, 0, initial + 1, 0, {"from": alice})


def test_insufficient_balance_erc20_returns_true_false(amm3, oracle, collateral3, alice):
    initial = collateral3.balanceOf(alice)
    amm3.exchange(0, 1, 1000 * 10**18, 0, {"from": alice})
    assert collateral3.balanceOf(alice) > initial

    oracle.set_price(5000 * 10**18, {"from": alice})
    initial = collateral3.balanceOf(alice)
    with brownie.reverts():
        amm3.exchange(1, 0, initial + 1, 0, {"from": alice})
