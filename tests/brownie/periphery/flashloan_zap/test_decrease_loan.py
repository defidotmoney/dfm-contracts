import brownie
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(controller, market, stable, collateral, zap, alice, deployer):
    collateral.approve(zap, 2**256 - 1, {"from": alice})
    collateral.approve(controller, 2**256 - 1, {"from": alice})

    collateral._mint_for_testing(alice, 5 * 10**18, {"from": alice})
    controller.setDelegateApproval(zap, True, {"from": alice})

    controller.create_loan(alice, market, 5 * 10**18, 10_000 * 10**18, 4, {"from": alice})
    stable.transfer(deployer, 10_000 * 10**18, {"from": alice})


def test_decrease_loan(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(collateral, stable, 3 * 10**18, 7_000 * 10**18)
    zap.decreaseLoan(market, 3 * 10**18, 7_000 * 10**18, data, {"from": alice})

    assert market.user_state(alice) == (2 * 10**18, 0, 3_000 * 10**18, 4)

    for acct in (alice, zap):
        assert stable.balanceOf(acct) == 0
        assert collateral.balanceOf(acct) == 0


def test_decrease_loan_excess_coll(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(collateral, stable, 2 * 10**18, 7_000 * 10**18)
    zap.decreaseLoan(market, 3 * 10**18, 7_000 * 10**18, data, {"from": alice})

    assert market.user_state(alice) == (2 * 10**18, 0, 3_000 * 10**18, 4)

    assert stable.balanceOf(zap) == 0
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 0
    assert collateral.balanceOf(alice) == 10**18


def test_decrease_loan_excess_debt(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(collateral, stable, 3 * 10**18, 7_500 * 10**18)
    zap.decreaseLoan(market, 3 * 10**18, 7_000 * 10**18, data, {"from": alice})

    assert market.user_state(alice) == (2 * 10**18, 0, 3_000 * 10**18, 4)

    assert stable.balanceOf(zap) == 0
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 500 * 10**18
    assert collateral.balanceOf(alice) == 0


def test_decrease_loan_excess_coll_and_debt(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(collateral, stable, 2 * 10**18, 7_500 * 10**18)
    zap.decreaseLoan(market, 3 * 10**18, 7_000 * 10**18, data, {"from": alice})

    assert market.user_state(alice) == (2 * 10**18, 0, 3_000 * 10**18, 4)

    assert stable.balanceOf(zap) == 0
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 500 * 10**18
    assert collateral.balanceOf(alice) == 10**18


def test_insufficient_coll_to_router(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(collateral, stable, 4 * 10**18, 7_000 * 10**18)
    with brownie.reverts("DFM: Odos router call failed"):
        zap.decreaseLoan(market, 3 * 10**18, 7_000 * 10**18, data, {"from": alice})


def test_insufficient_debt_to_repay_flashloan(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(collateral, stable, 3 * 10**18, 6_000 * 10**18)
    with brownie.reverts("ERC20: burn amount exceeds balance"):
        zap.decreaseLoan(market, 3 * 10**18, 7_000 * 10**18, data, {"from": alice})


def test_debt_too_high(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(stable, collateral, 20_000 * 10**18, 10**18)
    with brownie.reverts("DFM:M Debt too high"):
        zap.decreaseLoan(market, 4 * 10**18, 100 * 10**18, data, {"from": alice})
