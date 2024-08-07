import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(controller, market, stable, collateral, zap, alice):
    stable.approve(zap, 2**256 - 1, {"from": alice})
    collateral.approve(zap, 2**256 - 1, {"from": alice})
    collateral.approve(controller, 2**256 - 1, {"from": alice})

    collateral._mint_for_testing(alice, 15 * 10**18, {"from": alice})
    controller.setDelegateApproval(zap, True, {"from": alice})

    controller.create_loan(alice, market, 10 * 10**18, 10_000 * 10**18, 10, {"from": alice})


@pytest.mark.parametrize("debt_adjust", [0, 1_000 * 10**18, -3_000 * 10**18])
@pytest.mark.parametrize("coll_adjust", [0, 2 * 10**18, -(10**18)])
@pytest.mark.parametrize("num_bands", [4, 10, 20])
def test_no_route(market, stable, collateral, zap, alice, coll_adjust, debt_adjust, num_bands):
    initial_coll = collateral.balanceOf(alice)
    initial_debt = stable.balanceOf(alice)
    initial_state = market.user_state(alice)

    zap.closeAndCreateLoan(market, coll_adjust, debt_adjust, num_bands, b"", {"from": alice})

    assert collateral.balanceOf(alice) == initial_coll - coll_adjust
    assert stable.balanceOf(alice) == initial_debt + debt_adjust
    assert collateral.balanceOf(zap) == 0
    assert stable.balanceOf(zap) == 0

    assert market.user_state(alice) == (
        initial_state[0] + coll_adjust,
        0,
        initial_state[2] + debt_adjust,
        num_bands,
    )


@pytest.mark.parametrize("debt_adjust", [0, 1_000 * 10**18, -3_000 * 10**18])
@pytest.mark.parametrize("coll_adjust", [0, 2 * 10**18, -(10**18)])
@pytest.mark.parametrize("num_bands", [4, 10])
def test_sell_coll(
    market, stable, collateral, zap, router, alice, coll_adjust, debt_adjust, num_bands
):
    initial_coll = collateral.balanceOf(alice)
    initial_debt = stable.balanceOf(alice)
    initial_state = market.user_state(alice)

    data = router.mockSwap.encode_input(collateral, stable, 3 * 10**18, 1_000 * 10**18)
    zap.closeAndCreateLoan(market, coll_adjust, debt_adjust, num_bands, data, {"from": alice})

    assert collateral.balanceOf(alice) == initial_coll - coll_adjust
    assert stable.balanceOf(alice) == initial_debt + debt_adjust
    assert collateral.balanceOf(zap) == 0
    assert stable.balanceOf(zap) == 0

    assert market.user_state(alice) == (
        initial_state[0] + coll_adjust - 3 * 10**18,
        0,
        initial_state[2] + debt_adjust - 1_000 * 10**18,
        num_bands,
    )


@pytest.mark.parametrize("debt_adjust", [1_000 * 10**18, 3_000 * 10**18])
@pytest.mark.parametrize("coll_adjust", [0, 2 * 10**18, -(10**18)])
@pytest.mark.parametrize("num_bands", [4, 10])
def test_buy_coll(
    market, stable, collateral, zap, router, alice, coll_adjust, debt_adjust, num_bands
):
    initial_coll = collateral.balanceOf(alice)
    initial_debt = stable.balanceOf(alice)
    initial_state = market.user_state(alice)

    data = router.mockSwap.encode_input(stable, collateral, 1_000 * 10**18, 2 * 10**18)
    zap.closeAndCreateLoan(market, coll_adjust, debt_adjust, num_bands, data, {"from": alice})

    assert collateral.balanceOf(alice) == initial_coll - coll_adjust
    assert stable.balanceOf(alice) == initial_debt + debt_adjust
    assert collateral.balanceOf(zap) == 0
    assert stable.balanceOf(zap) == 0

    assert market.user_state(alice) == (
        initial_state[0] + coll_adjust + 2 * 10**18,
        0,
        initial_state[2] + debt_adjust + 1_000 * 10**18,
        num_bands,
    )
