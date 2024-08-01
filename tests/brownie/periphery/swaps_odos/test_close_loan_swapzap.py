import pytest
import brownie
from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(controller, market, stable, collateral_list, zap, alice):
    for token in collateral_list:
        token.approve(zap, 2**256 - 1, {"from": alice})
        token._mint_for_testing(alice, 10**18)

    controller.setDelegateApproval(zap, True, {"from": alice})
    stable.approve(zap, 2**256 - 1, {"from": alice})

    collateral_list[0]._mint_for_testing(alice, 5 * 10**18)
    collateral_list[0].approve(controller, 2**256 - 1, {"from": alice})
    controller.create_loan(alice, market, 5 * 10**18, 5_000 * 10**18, 10, {"from": alice})


@pytest.mark.parametrize("input_amount", [0, 2_000 * 10**18, 5_000 * 10**18])
@pytest.mark.parametrize("max_amount", [5_000 * 10**18, 2**256 - 1])
def test_no_swap(market, stable, collateral, zap, alice, input_amount, max_amount):
    input_data = ([(stable, input_amount)], b"")
    output_data = ([stable, collateral], b"")

    zap.closeLoan(market, max_amount, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (0, 0, 0, 10)

    assert collateral.balanceOf(alice) == 6 * 10**18
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == 0
    assert stable.balanceOf(zap) == 0


@pytest.mark.parametrize("swap_amount", [2_000 * 10**18, 5_000 * 10**18])
@pytest.mark.parametrize("max_amount", [5_000 * 10**18, 2**256 - 1])
def test_input_swap(
    market, stable, collateral, collateral2, router, zap, alice, swap_amount, max_amount
):
    route_calldata = router.mockSwapMulti.encode_input(
        [(collateral2, 10**18)], [(stable, swap_amount)]
    )
    input_data = ([(collateral2, 10**18)], route_calldata)
    output_data = ([stable, collateral], b"")

    zap.closeLoan(market, max_amount, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (0, 0, 0, 10)

    assert collateral.balanceOf(alice) == 6 * 10**18
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == swap_amount
    assert stable.balanceOf(zap) == 0


@pytest.mark.parametrize("swap_amount", [2_000 * 10**18, 5_000 * 10**18])
def test_input_swap_eth(market, stable, collateral, router, zap, alice, swap_amount):
    route_calldata = router.mockSwap.encode_input(ZERO_ADDRESS, stable, 10**18, swap_amount)
    input_data = ([], route_calldata)
    output_data = ([stable, collateral], b"")

    zap.closeLoan(market, 2**256 - 1, input_data, output_data, {"from": alice, "value": "1 ether"})

    assert market.user_state(alice) == (0, 0, 0, 10)

    assert collateral.balanceOf(alice) == 6 * 10**18
    assert collateral.balanceOf(zap) == 0

    assert stable.balanceOf(alice) == swap_amount
    assert stable.balanceOf(zap) == 0


@pytest.mark.parametrize("input_amount", [0, 2_000 * 10**18, 5_000 * 10**18])
@pytest.mark.parametrize("max_amount", [5_000 * 10**18, 2**256 - 1])
def test_output_swap(
    market, stable, collateral, collateral3, router, zap, alice, input_amount, max_amount
):
    input_data = ([(stable, input_amount)], b"")

    route_calldata = router.mockSwap.encode_input(collateral, collateral3, 2 * 10**18, 5 * 10**18)

    output_data = ([stable, collateral, collateral3], route_calldata)

    zap.closeLoan(market, max_amount, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (0, 0, 0, 10)

    assert collateral.balanceOf(alice) == 4 * 10**18
    assert collateral.balanceOf(zap) == 0

    assert collateral3.balanceOf(alice) == 6 * 10**18

    assert stable.balanceOf(alice) == 0
    assert stable.balanceOf(zap) == 0


def test_output_swap_eth(market, stable, collateral, router, zap, alice):
    input_data = ([], b"")
    route_calldata = router.mockSwap.encode_input(collateral, ZERO_ADDRESS, 2 * 10**18, 5 * 10**18)
    output_data = ([stable, collateral], route_calldata)

    initial = alice.balance()
    zap.closeLoan(market, 5_000 * 10**18, input_data, output_data, {"from": alice})

    assert market.user_state(alice) == (0, 0, 0, 10)

    assert collateral.balanceOf(alice) == 4 * 10**18
    assert collateral.balanceOf(zap) == 0

    assert alice.balance() == initial + 5 * 10**18

    assert stable.balanceOf(alice) == 0
    assert stable.balanceOf(zap) == 0
