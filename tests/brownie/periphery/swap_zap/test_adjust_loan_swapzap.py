import pytest
import brownie
from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(controller, market, stable, collateral_list, zap, alice, eth_receive_reverter):
    for acct in [alice, eth_receive_reverter]:
        for token in collateral_list:
            token.approve(zap, 2**256 - 1, {"from": acct})
            token._mint_for_testing(acct, 10**18)

        controller.setDelegateApproval(zap, True, {"from": acct})
        stable.approve(zap, 2**256 - 1, {"from": acct})

    collateral_list[0]._mint_for_testing(alice, 5 * 10**18)
    collateral_list[0].approve(controller, 2**256 - 1, {"from": alice})
    controller.create_loan(alice, market, 5 * 10**18, 5_000 * 10**18, 10, {"from": alice})


@pytest.mark.parametrize("debt_adjust", [-2000 * 10**18, 0, 1000 * 10**18])
@pytest.mark.parametrize("coll_adjust", [10**18, 0, -2 * 10**18])
def test_no_swap(market, stable, collateral, zap, alice, debt_adjust, coll_adjust):
    if debt_adjust == 0 and coll_adjust == 0:
        return

    input_data = ([(collateral, max(coll_adjust, 0)), (stable, max(0, -debt_adjust))], b"")
    output_data = ([stable, collateral], b"")

    zap.adjustLoan(market, coll_adjust, debt_adjust, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (
        5 * 10**18 + coll_adjust,
        0,
        5_000 * 10**18 + debt_adjust,
        10,
    )

    assert collateral.balanceOf(alice) == 10**18 - coll_adjust
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 5_000 * 10**18 + debt_adjust
    assert stable.balanceOf(zap) == 0


@pytest.mark.parametrize("debt_adjust", [-2000 * 10**18, 0])
@pytest.mark.parametrize("coll_adjust", [10**18, 0])
def test_input_swap(
    market, stable, collateral, collateral2, router, zap, alice, debt_adjust, coll_adjust
):
    if debt_adjust == 0 and coll_adjust == 0:
        return

    route_calldata = router.mockSwapMulti.encode_input(
        [(collateral2, 10**18)], [(collateral, coll_adjust), (stable, -debt_adjust)]
    )
    input_data = ([(collateral2, 10**18)], route_calldata)
    output_data = ([stable, collateral], b"")

    zap.adjustLoan(market, coll_adjust, debt_adjust, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (
        5 * 10**18 + coll_adjust,
        0,
        5_000 * 10**18 + debt_adjust,
        10,
    )

    assert collateral.balanceOf(alice) == 10**18
    assert collateral.balanceOf(zap) == 0

    assert collateral2.balanceOf(alice) == 0
    assert collateral2.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 5_000 * 10**18
    assert stable.balanceOf(zap) == 0


@pytest.mark.parametrize("debt_adjust", [-2000 * 10**18, 0])
@pytest.mark.parametrize("coll_adjust", [10**18, 0])
def test_input_swap_eth(market, stable, collateral, router, zap, alice, debt_adjust, coll_adjust):
    if debt_adjust == 0 and coll_adjust == 0:
        return

    route_calldata = router.mockSwapMulti.encode_input(
        [(ZERO_ADDRESS, 10**18)], [(collateral, coll_adjust), (stable, -debt_adjust)]
    )
    input_data = ([], route_calldata)
    output_data = ([stable, collateral], b"")

    zap.adjustLoan(
        market,
        coll_adjust,
        debt_adjust,
        input_data,
        output_data,
        {"from": alice, "value": "1 ether"},
    )

    assert market.user_state(alice) == (
        5 * 10**18 + coll_adjust,
        0,
        5_000 * 10**18 + debt_adjust,
        10,
    )

    assert collateral.balanceOf(alice) == 10**18
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 5_000 * 10**18
    assert stable.balanceOf(zap) == 0


@pytest.mark.parametrize("debt_adjust", [2000 * 10**18, 0])
@pytest.mark.parametrize("coll_adjust", [-(10**18), 0])
def test_output_swap(
    market, stable, collateral, collateral3, router, zap, alice, debt_adjust, coll_adjust
):
    if debt_adjust == 0 and coll_adjust == 0:
        return

    route_calldata = router.mockSwapMulti.encode_input(
        [(collateral, -coll_adjust), (stable, debt_adjust)], [(collateral3, 3 * 10**18)]
    )
    input_data = ([], b"")
    output_data = ([stable, collateral, collateral3], route_calldata)

    zap.adjustLoan(market, coll_adjust, debt_adjust, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (
        5 * 10**18 + coll_adjust,
        0,
        5_000 * 10**18 + debt_adjust,
        10,
    )

    assert collateral.balanceOf(alice) == 10**18
    assert collateral.balanceOf(zap) == 0

    assert collateral3.balanceOf(alice) == 4 * 10**18
    assert collateral3.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 5_000 * 10**18
    assert stable.balanceOf(zap) == 0


@pytest.mark.parametrize("debt_adjust", [2000 * 10**18, 0])
@pytest.mark.parametrize("coll_adjust", [-(10**18), 0])
def test_output_swap_eth(market, stable, collateral, router, zap, alice, debt_adjust, coll_adjust):
    if debt_adjust == 0 and coll_adjust == 0:
        return

    route_calldata = router.mockSwapMulti.encode_input(
        [(collateral, -coll_adjust), (stable, debt_adjust)], [(ZERO_ADDRESS, 3 * 10**18)]
    )
    input_data = ([], b"")
    output_data = ([stable, collateral], route_calldata)

    initial = alice.balance()
    zap.adjustLoan(market, coll_adjust, debt_adjust, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (
        5 * 10**18 + coll_adjust,
        0,
        5_000 * 10**18 + debt_adjust,
        10,
    )

    assert collateral.balanceOf(alice) == 10**18
    assert collateral.balanceOf(zap) == 0

    assert alice.balance() == initial + 3 * 10**18

    assert stable.balanceOf(alice) == 5_000 * 10**18
    assert stable.balanceOf(zap) == 0


@pytest.mark.parametrize("debt_adjust", [-2000 * 10**18, 0, 1000 * 10**18])
@pytest.mark.parametrize("coll_adjust", [10**18, 0, -2 * 10**18])
def test_complex(
    market,
    stable,
    collateral,
    collateral2,
    collateral3,
    router,
    zap,
    alice,
    debt_adjust,
    coll_adjust,
):
    if debt_adjust == 0 and coll_adjust == 0:
        return

    if coll_adjust > 0 or debt_adjust < 0:
        route_calldata = router.mockSwapMulti.encode_input(
            [(collateral2, 10**18)],
            [(collateral, max(0, coll_adjust)), (stable, max(0, -debt_adjust))],
        )
        input_data = ([(collateral2, 10**18)], route_calldata)
    else:
        input_data = ([], b"")

    if coll_adjust < 0 or debt_adjust > 0:
        route_calldata = router.mockSwapMulti.encode_input(
            [(collateral, max(0, -coll_adjust)), (stable, max(0, debt_adjust))],
            [(collateral3, 3 * 10**18)],
        )
    else:
        route_calldata = b""
    output_data = ([stable, collateral, collateral3], route_calldata)

    zap.adjustLoan(market, coll_adjust, debt_adjust, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (
        5 * 10**18 + coll_adjust,
        0,
        5_000 * 10**18 + debt_adjust,
        10,
    )

    assert collateral.balanceOf(alice) == 10**18
    assert collateral.balanceOf(zap) == 0

    expected = 0 if (coll_adjust > 0 or debt_adjust < 0) else 10**18
    assert collateral2.balanceOf(alice) == expected
    assert collateral2.balanceOf(zap) == 0

    expected = 4 * 10**18 if (coll_adjust < 0 or debt_adjust > 0) else 10**18
    assert collateral3.balanceOf(alice) == expected
    assert collateral3.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 5_000 * 10**18
    assert stable.balanceOf(zap) == 0


def test_max_coll_adjust(market, stable, collateral, collateral2, router, zap, alice):
    route_calldata = router.mockSwapMulti.encode_input(
        [(collateral2, 10**18)], [(collateral, 2 * 10**18)]
    )
    input_data = ([(collateral2, 10**18)], route_calldata)
    output_data = ([stable, collateral], b"")

    zap.adjustLoan(market, 2**255 - 1, 0, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (5 * 10**18 + 2 * 10**18, 0, 5_000 * 10**18, 10)

    assert collateral.balanceOf(alice) == 10**18
    assert collateral.balanceOf(zap) == 0

    assert collateral2.balanceOf(alice) == 0
    assert collateral2.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 5_000 * 10**18
    assert stable.balanceOf(zap) == 0


def test_min_debt_adjust(market, stable, collateral, collateral2, router, zap, alice):
    amount = 3000 * 10**18

    route_calldata = router.mockSwapMulti.encode_input([(collateral2, 10**18)], [(stable, amount)])
    input_data = ([(collateral2, 10**18)], route_calldata)
    output_data = ([stable, collateral], b"")

    zap.adjustLoan(market, 0, -(2**255), input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (5 * 10**18, 0, 5_000 * 10**18 - amount, 10)

    assert collateral.balanceOf(alice) == 10**18
    assert collateral.balanceOf(zap) == 0

    assert collateral2.balanceOf(alice) == 0
    assert collateral2.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 5_000 * 10**18
    assert stable.balanceOf(zap) == 0
