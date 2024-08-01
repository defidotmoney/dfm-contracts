import pytest
import brownie

from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module", autouse=True)
def setup(controller, collateral, stable, zap, alice, eth_receive_reverter):
    for acct in [alice, eth_receive_reverter]:
        collateral.approve(controller, 2**256 - 1, {"from": acct})
        collateral.approve(zap, 2**256 - 1, {"from": acct})
        collateral._mint_for_testing(acct, 6 * 10**18)

        controller.setDelegateApproval(zap, True, {"from": acct})
        stable.approve(zap, 2**256 - 1, {"from": acct})


def test_create_loan_msgvalue_without_route(market, stable, collateral, zap, alice):
    input_data = ([(collateral, 10**18)], b"")
    output_data = ([stable], b"")

    with brownie.reverts("DFM: msg.value > 0"):
        zap.createLoan(
            market,
            10**18,
            1_000 * 10**18,
            10,
            input_data,
            output_data,
            {"from": alice, "value": 10**18},
        )

    zap.createLoan(market, 10**18, 1_000 * 10**18, 10, input_data, output_data, {"from": alice})


def test_adjust_loan_msgvalue_without_route(controller, market, stable, collateral, zap, alice):
    controller.create_loan(alice, market, 5 * 10**18, 5_000 * 10**18, 10, {"from": alice})

    input_data = ([(collateral, 10**18)], b"")
    output_data = ([stable], b"")

    with brownie.reverts("DFM: msg.value > 0"):
        zap.adjustLoan(market, 10**18, 0, input_data, output_data, {"from": alice, "value": 10**18})

    zap.adjustLoan(market, 10**18, 0, input_data, output_data, {"from": alice})


def test_close_loan_msgvalue_without_route(market, stable, collateral, controller, zap, alice):
    controller.create_loan(alice, market, 5 * 10**18, 5_000 * 10**18, 10, {"from": alice})

    input_data = ([], b"")
    output_data = ([collateral, stable], b"")

    with brownie.reverts("DFM: msg.value > 0"):
        zap.closeLoan(market, 2**256 - 1, input_data, output_data, {"from": alice, "value": 10**18})

    zap.closeLoan(market, 2**256 - 1, input_data, output_data, {"from": alice})


def test_create_loan_caller_cannot_receive_eth(
    market, stable, collateral, router, zap, alice, eth_receive_reverter
):
    route_calldata = router.mockSwap.encode_input(stable, ZERO_ADDRESS, 1_000 * 10**18, 5 * 10**18)
    input_data = ([(collateral, 10**18)], b"")
    output_data = ([], route_calldata)

    with brownie.reverts("DFM: Transfer failed"):
        zap.createLoan(
            market,
            10**18,
            1_000 * 10**18,
            10,
            input_data,
            output_data,
            {"from": eth_receive_reverter},
        )

    # confirm the route works for a normal account
    zap.createLoan(market, 10**18, 1_000 * 10**18, 10, input_data, output_data, {"from": alice})


def test_adjust_loan_caller_cannot_receive_eth(
    controller, market, stable, router, zap, eth_receive_reverter
):
    controller.create_loan(
        eth_receive_reverter, market, 5 * 10**18, 5_000 * 10**18, 10, {"from": eth_receive_reverter}
    )

    route_calldata = router.mockSwap.encode_input(stable, ZERO_ADDRESS, 1_000 * 10**18, 5 * 10**18)
    input_data = ([], b"")
    output_data = ([], route_calldata)

    with brownie.reverts("DFM: Transfer failed"):
        zap.adjustLoan(
            market, 0, 1_000 * 10**18, input_data, output_data, {"from": eth_receive_reverter}
        )


def test_close_loan_caller_cannot_receive_eth(
    controller, market, collateral, router, zap, eth_receive_reverter
):
    controller.create_loan(
        eth_receive_reverter, market, 5 * 10**18, 5_000 * 10**18, 10, {"from": eth_receive_reverter}
    )

    route_calldata = router.mockSwap.encode_input(collateral, ZERO_ADDRESS, 10**18, 5 * 10**18)
    input_data = ([], b"")
    output_data = ([], route_calldata)

    with brownie.reverts("DFM: Transfer failed"):
        zap.closeLoan(market, 2**256 - 1, input_data, output_data, {"from": eth_receive_reverter})
