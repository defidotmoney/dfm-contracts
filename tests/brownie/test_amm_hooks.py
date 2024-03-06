import pytest
from brownie import ZERO_ADDRESS, compile_source


@pytest.fixture(scope="module")
def amm_hook(collateral, amm, deployer):
    HOOKS_SOURCE = """
# @version 0.3.7

from vyper.interfaces import ERC20

COLLATERAL: immutable(ERC20)
AMM: immutable(address)

@external
def __init__(collateral: ERC20, amm: address):
    COLLATERAL = collateral
    AMM = amm

@external
def on_add_hook(market: address, amm: address) -> bool:
    assert msg.sender == AMM
    amount: uint256 = COLLATERAL.balanceOf(AMM)
    COLLATERAL.transferFrom(AMM, self, amount)
    return True

@external
def on_remove_hook() -> bool:
    assert msg.sender == AMM
    amount: uint256 = COLLATERAL.balanceOf(self)
    COLLATERAL.transfer(msg.sender, amount)
    return True

@external
def before_collateral_out(amount: uint256) -> bool:
    COLLATERAL.transfer(AMM, amount)
    return True

@external
def after_collateral_in(amount: uint256) -> bool:
    COLLATERAL.transferFrom(AMM, self, amount)
    return True
"""
    return compile_source(HOOKS_SOURCE).Vyper.deploy(collateral, amm, {"from": deployer})


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, controller, market, alice, deployer):

    for acct in [deployer, alice]:
        collateral._mint_for_testing(acct, 100 * 10**18)
        collateral.approve(controller, 2**256 - 1, {"from": acct})

    controller.create_loan(deployer, market, 100 * 10**18, 100_000 * 10**18, 5, {"from": deployer})


def test_on_add(collateral, market, controller, amm, amm_hook, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})

    assert amm.exchange_hook() == amm_hook
    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == 100 * 10**18


def test_on_remove(collateral, market, controller, amm, amm_hook, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})

    controller.set_amm_hook(market, ZERO_ADDRESS, {"from": deployer})

    assert amm.exchange_hook() == ZERO_ADDRESS
    assert collateral.balanceOf(amm) == 100 * 10**18
    assert collateral.balanceOf(amm_hook) == 0


def test_collateral_in(collateral, market, controller, amm, amm_hook, alice, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})

    controller.create_loan(alice, market, 50 * 10**18, 10_000 * 10**18, 5, {"from": alice})

    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == 150 * 10**18


def test_collateral_out(collateral, market, controller, amm, amm_hook, alice, deployer):
    controller.set_amm_hook(market, amm_hook, {"from": deployer})

    controller.create_loan(alice, market, 50 * 10**18, 10_000 * 10**18, 5, {"from": alice})
    controller.adjust_loan(alice, market, -40 * 10**18, 0, {"from": alice})

    assert collateral.balanceOf(amm) == 0
    assert collateral.balanceOf(amm_hook) == 110 * 10**18


# TODO test other paths to coll in / out
# TODO test hooks with AMM exchanges
