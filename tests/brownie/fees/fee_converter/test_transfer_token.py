import brownie
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, converter):
    collateral._mint_for_testing(converter, 100000)


def test_transfer_token_full(converter, collateral, alice, deployer):
    converter.transferToken(collateral, alice, 100000, {"from": deployer})
    assert collateral.balanceOf(alice) == 100000
    assert collateral.balanceOf(converter) == 0


def test_transfer_token_partial(converter, collateral, alice, deployer):
    converter.transferToken(collateral, alice, 40000, {"from": deployer})
    assert collateral.balanceOf(alice) == 40000
    assert collateral.balanceOf(converter) == 60000


def test_transfer_token_zero(converter, collateral, alice, deployer):
    converter.transferToken(collateral, alice, 0, {"from": deployer})
    assert collateral.balanceOf(alice) == 0
    assert collateral.balanceOf(converter) == 100000


def test_transfer_token_exceeds_balance(converter, collateral, alice, deployer):
    with brownie.reverts():
        converter.transferToken(collateral, alice, 100001, {"from": deployer})


def test_onlyowner(converter, collateral, alice):
    with brownie.reverts("DFM: Only owner"):
        converter.transferToken(collateral, alice, 100000, {"from": alice})
