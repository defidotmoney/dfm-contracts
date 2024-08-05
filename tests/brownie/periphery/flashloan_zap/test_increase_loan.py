import brownie
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(controller, market, stable, collateral, zap, alice, deployer):
    collateral.approve(zap, 2**256 - 1, {"from": alice})
    collateral.approve(controller, 2**256 - 1, {"from": alice})

    collateral._mint_for_testing(alice, 5 * 10**18, {"from": alice})
    controller.setDelegateApproval(zap, True, {"from": alice})

    controller.create_loan(alice, market, 5 * 10**18, 5_000 * 10**18, 4, {"from": alice})
    stable.transfer(deployer, 5_000 * 10**18, {"from": alice})


@pytest.mark.parametrize("coll_amount", [0, 10**18])
def test_increase_loan(market, stable, collateral, router, zap, alice, coll_amount):
    collateral._mint_for_testing(alice, coll_amount, {"from": alice})
    data = router.mockSwap.encode_input(stable, collateral, 10_000 * 10**18, 3 * 10**18)
    zap.increaseLoan(market, coll_amount, 10_000 * 10**18, data, {"from": alice})

    assert market.user_state(alice) == (coll_amount + 8 * 10**18, 0, 15_000 * 10**18, 4)

    for acct in (alice, zap):
        assert stable.balanceOf(acct) == 0
        assert collateral.balanceOf(acct) == 0


@pytest.mark.parametrize("coll_amount", [0, 10**18])
def test_increase_loan_excess_debt(market, stable, collateral, router, zap, alice, coll_amount):
    collateral._mint_for_testing(alice, coll_amount, {"from": alice})
    data = router.mockSwap.encode_input(stable, collateral, 8_500 * 10**18, 3 * 10**18)
    zap.increaseLoan(market, coll_amount, 10_000 * 10**18, data, {"from": alice})

    assert market.user_state(alice) == (coll_amount + 8 * 10**18, 0, 13_500 * 10**18, 4)

    for acct in (alice, zap):
        assert stable.balanceOf(acct) == 0
        assert collateral.balanceOf(acct) == 0


def test_insufficient_debt_to_router(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(stable, collateral, 11_000 * 10**18, 4 * 10**18)
    with brownie.reverts("DFM: Odos router call failed"):
        zap.increaseLoan(market, 0, 10_000 * 10**18, data, {"from": alice})


def test_insufficient_coll_to_create(market, stable, collateral, router, zap, alice):
    data = router.mockSwap.encode_input(stable, collateral, 20_000 * 10**18, 10**18)
    with brownie.reverts("DFM:M Debt too high"):
        zap.increaseLoan(market, 0, 20_000 * 10**18, data, {"from": alice})


@pytest.mark.parametrize("amount", [10000, 25000])
def test_zap_balance_exceeds_debt(
    market, stable, controller, collateral, router, zap, alice, amount
):
    amount *= 10**18
    stable.mint(zap, amount, {"from": controller})
    collateral._mint_for_testing(alice, 10**18, {"from": alice})
    data = router.mockSwap.encode_input(stable, collateral, 10_000 * 10**18, 3 * 10**18)
    zap.increaseLoan(market, 10**18, 10_000 * 10**18, data, {"from": alice})

    assert market.user_state(alice) == (9 * 10**18, 0, 5_000 * 10**18, 4)

    assert stable.balanceOf(alice) == 0
    assert collateral.balanceOf(alice) == 0

    assert stable.balanceOf(zap) == amount - 10_000 * 10**18
    assert collateral.balanceOf(zap) == 0
