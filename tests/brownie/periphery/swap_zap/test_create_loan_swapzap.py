import pytest
import brownie
from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(controller, collateral_list, zap, alice, eth_receive_reverter):
    for acct in [alice, eth_receive_reverter]:
        for token in collateral_list:
            token.approve(zap, 2**256 - 1, {"from": acct})
            token._mint_for_testing(acct, 10**18)

        controller.setDelegateApproval(zap, True, {"from": acct})


def test_no_swap(market, stable, collateral, router, zap, alice):
    input_data = ([(collateral, 10**18)], b"")
    output_data = ([stable], b"")

    zap.createLoan(market, 10**18, 1_000 * 10**18, 4, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (10**18, 0, 1_000 * 10**18, 4)

    assert collateral.balanceOf(alice) == 0
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 1_000 * 10**18
    assert stable.balanceOf(zap) == 0


def test_input_swap_simple(market, stable, collateral, collateral2, router, zap, alice):
    route_calldata = router.mockSwap.encode_input(collateral2, collateral, 10**18, 5 * 10**18)
    input_data = ([(collateral2, 10**18)], route_calldata)
    output_data = ([stable], b"")

    zap.createLoan(market, 5 * 10**18, 8_000 * 10**18, 5, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (5 * 10**18, 0, 8_000 * 10**18, 5)

    assert collateral.balanceOf(alice) == 10**18
    assert collateral.balanceOf(zap) == 0

    assert collateral2.balanceOf(alice) == 0
    assert collateral2.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 8_000 * 10**18
    assert stable.balanceOf(zap) == 0


def test_input_swap_msgvalue(market, stable, collateral, router, zap, alice):
    route_calldata = router.mockSwap.encode_input(ZERO_ADDRESS, collateral, 10**18, 5 * 10**18)
    input_data = ([], route_calldata)
    output_data = ([stable], b"")

    initial = alice.balance()
    zap.createLoan(
        market,
        5 * 10**18,
        8_000 * 10**18,
        5,
        input_data,
        output_data,
        {"from": alice, "value": 10**18},
    )

    assert market.user_state(alice) == (5 * 10**18, 0, 8_000 * 10**18, 5)

    assert collateral.balanceOf(alice) == 10**18
    assert collateral.balanceOf(zap) == 0

    assert alice.balance() == initial - 10**18

    assert stable.balanceOf(alice) == 8_000 * 10**18
    assert stable.balanceOf(zap) == 0


def test_input_swap_multi(market, stable, collateral, collateral2, collateral3, router, zap, alice):
    route_calldata = router.mockSwapMulti.encode_input(
        [(collateral2, 10**18), (collateral3, 10**18)], [(collateral, 4 * 10**18)]
    )
    input_data = (
        [(collateral, 10**18), (collateral2, 10**18), (collateral3, 10**18)],
        route_calldata,
    )
    output_data = ([stable], b"")

    zap.createLoan(market, 5 * 10**18, 11_000 * 10**18, 5, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (5 * 10**18, 0, 11_000 * 10**18, 5)

    for token in [collateral, collateral2, collateral3]:
        assert token.balanceOf(alice) == 0
        assert token.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 11_000 * 10**18
    assert stable.balanceOf(zap) == 0


def test_output_swap_simple(market, stable, collateral, collateral3, router, zap, alice):
    route_calldata = router.mockSwap.encode_input(stable, collateral3, 1_000 * 10**18, 5 * 10**18)
    input_data = ([(collateral, 10**18)], b"")
    output_data = ([collateral3], route_calldata)

    zap.createLoan(market, 10**18, 1_000 * 10**18, 10, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (10**18, 0, 1_000 * 10**18, 10)

    assert collateral.balanceOf(alice) == 0
    assert collateral.balanceOf(zap) == 0

    assert collateral3.balanceOf(alice) == 6 * 10**18
    assert collateral3.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 0
    assert stable.balanceOf(zap) == 0


def test_output_swap_native(market, stable, collateral, collateral3, router, zap, alice):
    route_calldata = router.mockSwap.encode_input(stable, ZERO_ADDRESS, 1_000 * 10**18, 5 * 10**18)
    input_data = ([(collateral, 10**18)], b"")
    output_data = ([], route_calldata)

    initial = alice.balance()
    zap.createLoan(market, 10**18, 1_000 * 10**18, 10, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (10**18, 0, 1_000 * 10**18, 10)

    assert collateral.balanceOf(alice) == 0
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 0
    assert stable.balanceOf(zap) == 0

    assert alice.balance() == initial + 5 * 10**18


def test_output_swap_multi(
    market, stable, collateral, collateral2, collateral3, router, zap, alice
):
    route_calldata = router.mockSwapMulti.encode_input(
        [(stable, 1500 * 10**18)], [(collateral2, 10**18), (collateral3, 2 * 10**18)]
    )
    input_data = ([(collateral, 10**18)], b"")
    output_data = ([stable, collateral2, collateral3], route_calldata)

    zap.createLoan(market, 10**18, 2_000 * 10**18, 10, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (10**18, 0, 2_000 * 10**18, 10)

    assert collateral.balanceOf(alice) == 0
    assert collateral.balanceOf(zap) == 0

    assert collateral2.balanceOf(alice) == 2 * 10**18
    assert collateral2.balanceOf(zap) == 0

    assert collateral3.balanceOf(alice) == 3 * 10**18
    assert collateral3.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 500 * 10**18
    assert stable.balanceOf(zap) == 0


def test_complex(market, stable, collateral, collateral2, collateral3, router, zap, alice):
    route_calldata = router.mockSwapMulti.encode_input(
        [(ZERO_ADDRESS, 2 * 10**18), (collateral2, 10**18)], [(collateral, 5 * 10**18)]
    )
    input_data = ([(collateral, 10**18), (collateral2, 10**18)], route_calldata)
    route_calldata = router.mockSwapMulti.encode_input(
        [(stable, 5_000 * 10**18)], [(collateral3, 10**18), (ZERO_ADDRESS, 3 * 10**18)]
    )
    output_data = ([stable, collateral3], route_calldata)

    initial = alice.balance()

    zap.createLoan(
        market,
        6 * 10**18,
        9_000 * 10**18,
        10,
        input_data,
        output_data,
        {"from": alice, "value": "2 ether"},
    )

    assert market.user_state(alice) == (6 * 10**18, 0, 9_000 * 10**18, 10)

    assert collateral.balanceOf(alice) == 0
    assert collateral.balanceOf(zap) == 0

    assert collateral2.balanceOf(alice) == 0
    assert collateral2.balanceOf(zap) == 0

    assert collateral3.balanceOf(alice) == 2 * 10**18
    assert collateral3.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 4_000 * 10**18
    assert stable.balanceOf(zap) == 0

    assert alice.balance() == initial + 10**18
