import pytest
from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, alice, controller):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})


def test_create_loan(market, controller, alice):
    tx = controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    assert "PriceWrite" in tx.events


@pytest.mark.parametrize("coll_change", [5 * 10**18, -8 * 10**18])
@pytest.mark.parametrize("debt_change", [10**20, -5 * 10**19])
def test_adjust_coll_and_debt(market, controller, alice, coll_change, debt_change):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    tx = controller.adjust_loan(alice, market, coll_change, debt_change, {"from": alice})

    assert "PriceWrite" in tx.events


def test_repay_unhealthy(controller, amm, market, oracle, stable, alice):
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    oracle.set_price(500 * 10**18, {"from": alice})
    stable.approve(amm, 2**256 - 1, {"from": alice})
    amm.exchange(0, 1, 50_000 * 10**18, 0, {"from": alice})

    assert market.health(alice) < 0
    tx = controller.adjust_loan(alice, market, 0, -50_000 * 10**18, {"from": alice})

    assert "PriceWrite" in tx.events


def test_close(market, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
    tx = controller.close_loan(alice, market, {"from": alice})

    assert "PriceWrite" not in tx.events


def test_close_without_oracle(market, amm, controller, alice):
    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})

    # hacky - remove oracle in AMM directly to bypass normal checks
    amm.set_oracle(ZERO_ADDRESS, {"from": market})

    controller.close_loan(alice, market, {"from": alice})


def test_amm_exchange(controller, amm, market, oracle, stable, alice):
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    oracle.set_price(500 * 10**18, {"from": alice})
    stable.approve(amm, 2**256 - 1, {"from": alice})
    tx = amm.exchange(0, 1, 50_000 * 10**18, 0, {"from": alice})

    assert "PriceWrite" in tx.events
