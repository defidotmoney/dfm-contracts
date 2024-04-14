import brownie
import pytest
from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, stable, controller, market, amm, alice, deployer):

    for acct in [deployer, alice]:
        collateral._mint_for_testing(acct, 100 * 10**18)
        collateral.approve(controller, 2**256 - 1, {"from": acct})

    controller.create_loan(deployer, market, 100 * 10**18, 100_000 * 10**18, 5, {"from": deployer})

    stable.approve(amm, 2**256 - 1, {"from": alice})
    collateral.approve(amm, 2**256 - 1, {"from": alice})


def test_initial_collateral_balance(amm):
    assert amm.collateral_balance() == 100 * 10**18


def test_on_add(collateral, market, controller, amm, amm_hook, deployer):
    tx = controller.set_amm_hook(market, amm_hook, {"from": deployer})

    assert "OnAddHook" in tx.events
    assert amm.exchange_hook() == amm_hook
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == 100 * 10**18
    assert amm.collateral_balance() == 100 * 10**18


def test_on_remove(collateral, market, controller, amm, amm_hook, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    tx = controller.set_amm_hook(market, ZERO_ADDRESS, {"from": deployer})

    assert "OnRemoveHook" in tx.events
    assert amm.exchange_hook() == ZERO_ADDRESS
    assert collateral.balanceOf(amm) == 100 * 10**18
    assert collateral.balanceOf(amm_hook) == 0
    assert amm.collateral_balance() == 100 * 10**18


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


def test_on_add_reverts(market, controller, amm_hook, deployer):
    amm_hook.set_is_reverting(True, {"from": deployer})
    with brownie.reverts("AMM Hook is reverting"):
        controller.set_amm_hook(market, amm_hook, {"from": deployer})


def test_on_remove_reverts(market, controller, amm_hook, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})

    amm_hook.set_is_reverting(True, {"from": deployer})
    with brownie.reverts("AMM Hook is reverting"):
        controller.set_amm_hook(market, ZERO_ADDRESS, {"from": deployer})


def test_coll_in_reverts(market, controller, amm_hook, alice, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    amm_hook.set_is_reverting(True, {"from": deployer})

    with brownie.reverts("AMM Hook is reverting"):
        controller.create_loan(alice, market, 50 * 10**18, 10_000 * 10**18, 5, {"from": alice})


def test_coll_out_reverts(market, controller, amm_hook, alice, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    controller.create_loan(alice, market, 50 * 10**18, 10_000 * 10**18, 5, {"from": alice})
    amm_hook.set_is_reverting(True, {"from": deployer})

    with brownie.reverts("AMM Hook is reverting"):
        controller.adjust_loan(alice, market, -40 * 10**18, 0, {"from": alice})


def test_set_hook_balance_changed(market, controller, amm_hook, deployer):
    amm_hook.set_is_transfer_enabled(False, {"from": deployer})
    with brownie.reverts("DFM:C balance changed"):
        controller.set_amm_hook(market, amm_hook, {"from": deployer})


def test_remove_hook_balance_changed(market, controller, amm_hook, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})
    amm_hook.set_is_transfer_enabled(False, {"from": deployer})
    with brownie.reverts("DFM:C balance changed"):
        controller.set_amm_hook(market, ZERO_ADDRESS, {"from": deployer})


def test_add_remove_erc20_returns_none(
    AmmHookTester, controller, collateral2, market2, amm2, alice, deployer
):
    collateral2._mint_for_testing(alice, 100 * 10**18)
    collateral2.approve(controller, 2**256 - 1, {"from": alice})
    controller.create_loan(alice, market2, 100 * 10**18, 100_000 * 10**18, 5, {"from": alice})

    amm_hook = AmmHookTester.deploy(controller, collateral2, amm2, {"from": deployer})
    controller.set_amm_hook(market2, amm_hook, {"from": deployer})
    assert collateral2.balanceOf(amm2) == 0
    assert collateral2.balanceOf(amm_hook) == 100 * 10**18

    controller.set_amm_hook(market2, ZERO_ADDRESS, {"from": deployer})
    assert collateral2.balanceOf(amm2) == 100 * 10**18
    assert collateral2.balanceOf(amm_hook) == 0
