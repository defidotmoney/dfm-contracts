import brownie
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(controller, market, stable, collateral, zap, alice, deployer):
    stable.approve(zap, 2**256 - 1, {"from": alice})
    collateral.approve(controller, 2**256 - 1, {"from": alice})

    collateral._mint_for_testing(alice, 5 * 10**18, {"from": alice})
    controller.setDelegateApproval(zap, True, {"from": alice})

    controller.create_loan(alice, market, 5 * 10**18, 10_000 * 10**18, 4, {"from": alice})


def test_close_loan_no_debt(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(collateral, stable, 3 * 10**18, 10_000 * 10**18)
    zap.closeLoan(market, 0, data, {"from": alice})

    assert market.debt(alice) == 0

    assert stable.balanceOf(zap) == 0
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 10_000 * 10**18
    assert collateral.balanceOf(alice) == 2 * 10**18


def test_close_loan_some_debt(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(collateral, stable, 1 * 10**18, 3_000 * 10**18)
    zap.closeLoan(market, 7_000 * 10**18, data, {"from": alice})

    assert market.debt(alice) == 0

    assert stable.balanceOf(zap) == 0
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 3_000 * 10**18
    assert collateral.balanceOf(alice) == 4 * 10**18


def test_close_loan_excess_debt(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(collateral, stable, 1 * 10**18, 4_000 * 10**18)
    zap.closeLoan(market, 7_000 * 10**18, data, {"from": alice})

    assert market.debt(alice) == 0

    assert stable.balanceOf(zap) == 0
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 4_000 * 10**18
    assert collateral.balanceOf(alice) == 4 * 10**18


def test_close_loan_nothing_returned(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(collateral, stable, 5 * 10**18, 10_000 * 10**18)
    zap.closeLoan(market, 0, data, {"from": alice})

    assert market.debt(alice) == 0

    assert stable.balanceOf(zap) == 0
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 10_000 * 10**18
    assert collateral.balanceOf(alice) == 0


def test_close_no_shortfall(market, stable, router, zap, alice):
    stable.transfer(alice, 1_000 * 10**18, {"from": router})
    with brownie.reverts():
        zap.closeLoan(market, 11_000 * 10**18, b"", {"from": alice})


def test_close_no_debt(market, stable, router, zap, bob):
    stable.transfer(bob, 1_000 * 10**18, {"from": router})
    stable.approve(zap, 2**256 - 1, {"from": bob})
    with brownie.reverts("DFM: No debt owed"):
        zap.closeLoan(market, 1_000 * 10**18, b"", {"from": bob})
