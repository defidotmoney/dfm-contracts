import pytest
import brownie


@pytest.fixture(scope="module", autouse=True)
def setup_base(alice, stable, controller):
    stable.mint(alice, 10**20, {"from": controller})


@pytest.fixture(scope="module", autouse=True)
def setup_parametrized(collateral1, converter, alice, stable):
    collateral1._mint_for_testing(converter, 10**18)
    stable.approve(converter, 2**256 - 1, {"from": alice})


def test_slippage(converter, collateral1, alice):
    expected_out = converter.getSwapDebtForCollAmountOut(collateral1, 10**20)
    with brownie.reverts("DFM: Slippage"):
        converter.swapDebtForColl(collateral1, 10**20, expected_out + 1, {"from": alice})


def test_insufficient_amount_in(converter, collateral1, alice):
    with brownie.reverts("ERC20: transfer amount exceeds balance"):
        converter.swapDebtForColl(collateral1, 10**20 + 1, 0, {"from": alice})


def test_insufficient_amount_out(converter, stable, controller, collateral1, alice):
    stable.mint(alice, 10**24, {"from": controller})
    with brownie.reverts("SafeERC20: low-level call failed"):
        converter.swapDebtForColl(collateral1, 10**24, 0, {"from": alice})
