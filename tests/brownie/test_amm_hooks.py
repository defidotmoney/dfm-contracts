import pytest
from brownie import ZERO_ADDRESS, compile_source


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, stable, controller, market, amm, alice, deployer):

    for acct in [deployer, alice]:
        collateral._mint_for_testing(acct, 100 * 10**18)
        collateral.approve(controller, 2**256 - 1, {"from": acct})

    controller.create_loan(deployer, market, 100 * 10**18, 100_000 * 10**18, 5, {"from": deployer})

    stable.approve(amm, 2**256 - 1, {"from": alice})
    collateral.approve(amm, 2**256 - 1, {"from": alice})


def test_on_add(collateral, market, controller, amm, amm_hook, deployer):
    tx = controller.set_amm_hook(market, amm_hook, {"from": deployer})

    assert "OnAddHook" in tx.events
    assert amm.exchange_hook() == amm_hook
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == 100 * 10**18


def test_on_remove(collateral, market, controller, amm, amm_hook, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    tx = controller.set_amm_hook(market, ZERO_ADDRESS, {"from": deployer})

    assert "OnRemoveHook" in tx.events
    assert amm.exchange_hook() == ZERO_ADDRESS
    assert collateral.balanceOf(amm) == 100 * 10**18
    assert collateral.balanceOf(amm_hook) == 0


def test_coll_in_create(collateral, market, controller, amm, amm_hook, alice, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    tx = controller.create_loan(alice, market, 50 * 10**18, 10_000 * 10**18, 5, {"from": alice})

    assert "AfterCollIn" in tx.events
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == 150 * 10**18


def test_coll_in_adjust(collateral, market, controller, amm, amm_hook, alice, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    controller.create_loan(alice, market, 50 * 10**18, 10_000 * 10**18, 5, {"from": alice})
    tx = controller.adjust_loan(alice, market, 10 * 10**18, 0, {"from": alice})

    assert "AfterCollIn" in tx.events
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == 160 * 10**18


def test_coll_out_adjust(collateral, market, controller, amm, amm_hook, alice, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    controller.create_loan(alice, market, 50 * 10**18, 10_000 * 10**18, 5, {"from": alice})
    tx = controller.adjust_loan(alice, market, -40 * 10**18, 0, {"from": alice})

    assert "BeforeCollOut" in tx.events
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == 110 * 10**18


def test_coll_out_close(collateral, market, controller, amm, amm_hook, alice, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    controller.create_loan(alice, market, 50 * 10**18, 10_000 * 10**18, 5, {"from": alice})
    tx = controller.close_loan(alice, market, {"from": alice})

    assert "BeforeCollOut" in tx.events
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == 100 * 10**18


def test_coll_out_liquidate(collateral, market, controller, amm, amm_hook, oracle, alice, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    oracle.set_price(2100 * 10**18, {"from": alice})
    tx = controller.liquidate(market, alice, 0, {"from": alice})

    assert "BeforeCollOut" in tx.events
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == 100 * 10**18


def test_coll_out_collect_fees(
    collateral, stable, market, controller, amm, amm_hook, alice, deployer, fee_receiver
):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})

    amm.exchange(0, 1, 10_000 * 10**18, 0, {"from": alice})
    amm.exchange(1, 0, 10 * 10**18, 0, {"from": alice})

    tx = controller.collect_fees([market], {"from": deployer})

    assert "BeforeCollOut" in tx.events
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(fee_receiver) > 0


def test_coll_out_amm_exchange(
    collateral, stable, market, controller, amm, amm_hook, alice, deployer
):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})

    initial = collateral.balanceOf(alice)
    expected = amm.get_dy(0, 1, 10_000 * 10**18)
    tx = amm.exchange(0, 1, 10_000 * 10**18, 0, {"from": alice})

    assert "BeforeCollOut" in tx.events
    assert expected > 0
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(alice) == expected + initial


def test_coll_in_amm_exchange(
    collateral, stable, market, controller, amm, amm_hook, alice, deployer
):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    controller.create_loan(alice, market, 50 * 10**18, 100_000 * 10**18, 5, {"from": alice})
    amm.exchange(0, 1, 10_000 * 10**18, 0, {"from": alice})

    initial = collateral.balanceOf(amm_hook)
    expected = amm.get_dy(1, 0, 10 * 10**18)
    tx = amm.exchange(1, 0, 10**18, 0, {"from": alice})

    assert "AfterCollIn" in tx.events
    assert expected > 0
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == initial + 10**18
