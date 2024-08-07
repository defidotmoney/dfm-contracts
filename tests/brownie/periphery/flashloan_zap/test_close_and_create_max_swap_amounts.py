import brownie
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(controller, market, stable, collateral, zap, alice):
    stable.approve(zap, 2**256 - 1, {"from": alice})
    collateral.approve(zap, 2**256 - 1, {"from": alice})
    collateral.approve(controller, 2**256 - 1, {"from": alice})

    collateral._mint_for_testing(alice, 15 * 10**18, {"from": alice})
    controller.setDelegateApproval(zap, True, {"from": alice})

    controller.create_loan(alice, market, 10 * 10**18, 10_000 * 10**18, 10, {"from": alice})


@pytest.mark.parametrize("debt_adjust", [-500 * 10**18, 0, 1_000 * 10**18, 3_000 * 10**18])
def test_max_stable_amount(market, stable, collateral, zap, router, alice, debt_adjust):

    data = router.mockSwap.encode_input(stable, collateral, max(debt_adjust, 0) + 1, 2 * 10**18)
    with brownie.reverts("DFM: Odos router call failed"):
        zap.closeAndCreateLoan(market, 0, debt_adjust, 10, data, {"from": alice})

    data = router.mockSwap.encode_input(stable, collateral, max(debt_adjust, 0), 2 * 10**18)
    zap.closeAndCreateLoan(market, 0, debt_adjust, 10, data, {"from": alice})


@pytest.mark.parametrize("coll_adjust", [-5 * 10**18, 0, 3 * 10**18])
def test_max_coll_amount(market, stable, collateral, zap, router, alice, coll_adjust):

    data = router.mockSwap.encode_input(
        collateral, stable, 10 * 10**18 + max(coll_adjust, 0) + 1, 1_000 * 10**18
    )

    with brownie.reverts("DFM: Odos router call failed"):
        zap.closeAndCreateLoan(market, coll_adjust, 0, 10, data, {"from": alice})

    data = router.mockSwap.encode_input(
        collateral, stable, 10 * 10**18 + max(coll_adjust, 0), 1_000 * 10**18
    )

    with brownie.reverts("DFM: No collateral" if coll_adjust < 0 else "DFM:C 0 coll or debt"):
        zap.closeAndCreateLoan(market, coll_adjust, 0, 10, data, {"from": alice})
