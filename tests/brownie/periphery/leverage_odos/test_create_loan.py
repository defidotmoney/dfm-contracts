import brownie
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(controller, stable, collateral, zap, alice):
    collateral.approve(zap, 2**256 - 1, {"from": alice})

    collateral._mint_for_testing(alice, 10**18, {"from": alice})
    controller.setDelegateApproval(zap, True, {"from": alice})


def test_create_loan(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(stable, collateral, 10_000 * 10**18, 4 * 10**18)
    zap.createLoan(market, 10**18, 10_000 * 10**18, 4, data, {"from": alice})

    assert market.user_state(alice) == (5 * 10**18, 0, 10_000 * 10**18, 4)

    for acct in (alice, zap):
        assert stable.balanceOf(acct) == 0
        assert collateral.balanceOf(acct) == 0


def test_create_loan_excess_debt(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(stable, collateral, 8_500 * 10**18, 4 * 10**18)
    zap.createLoan(market, 10**18, 10_000 * 10**18, 4, data, {"from": alice})

    assert market.user_state(alice) == (5 * 10**18, 0, 8_500 * 10**18, 4)

    for acct in (alice, zap):
        assert stable.balanceOf(acct) == 0
        assert collateral.balanceOf(acct) == 0


def test_insufficient_debt_to_router(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(stable, collateral, 11_000 * 10**18, 4 * 10**18)
    with brownie.reverts("DFM: Odos router call failed"):
        zap.createLoan(market, 10**18, 10_000 * 10**18, 4, data, {"from": alice})


def test_insufficient_coll_to_create(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(stable, collateral, 10_000 * 10**18, 1 * 10**18)
    with brownie.reverts("DFM:M Debt too high"):
        zap.createLoan(market, 10**18, 10_000 * 10**18, 4, data, {"from": alice})


def test_invalid_market(zap, alice):
    with brownie.reverts("DFM: Market does not exist"):
        zap.createLoan(alice, 10**18, 10_000 * 10**18, 4, b"", {"from": alice})
