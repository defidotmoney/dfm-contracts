import brownie
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(controller, market, stable, collateral, amm, dummy_oracle, zap, alice, bob, deployer):
    stable.approve(zap, 2**256 - 1, {"from": alice})
    collateral.approve(controller, 2**256 - 1, {"from": alice})
    collateral.approve(zap, 2**256 - 1, {"from": alice})

    stable.mint(bob, 100_000 * 10**18, {"from": controller})
    stable.approve(amm, 2**256 - 1, {"from": bob})

    collateral._mint_for_testing(alice, 10 * 10**18, {"from": alice})
    controller.setDelegateApproval(zap, True, {"from": alice})

    controller.create_loan(alice, market, 5 * 10**18, 10_000 * 10**18, 10, {"from": alice})
    band = amm.read_user_tick_numbers(alice)[0] + 5
    price = amm.p_oracle_up(band)
    dummy_oracle.set_price(price, {"from": deployer})
    amm.exchange(0, 1, 6000 * 10**18, 0, {"from": bob})


def test_initial_setup(controller, market, amm, alice):
    assert min(amm.get_sum_xy(alice)) > 0


def test_add_coll(market, amm, collateral, stable, router, zap, alice):
    stable_amount, coll_amount = amm.get_sum_xy(alice)
    data = router.mockSwap.encode_input(stable, collateral, stable_amount, 2 * 10**18)
    zap.addCollateral(market, 10**18, 0, 10, data, {"from": alice})

    assert amm.get_sum_xy(alice) == (0, coll_amount + 3 * 10**18)
    assert market.debt(alice) == 10_000 * 10**18

    assert stable.balanceOf(alice) == 10_000 * 10**18
    assert stable.balanceOf(zap) == 0

    assert collateral.balanceOf(alice) == 4 * 10**18
    assert collateral.balanceOf(zap) == 0


@pytest.mark.parametrize("num_bands", [4, 10, 20])
def test_add_coll_modify_num_bands(market, amm, collateral, stable, router, zap, alice, num_bands):
    stable_amount = amm.get_sum_xy(alice)[0]
    data = router.mockSwap.encode_input(stable, collateral, stable_amount, 2 * 10**18)
    zap.addCollateral(market, 10**18, 0, num_bands, data, {"from": alice})

    bands = amm.read_user_tick_numbers(alice)
    assert bands[1] + 1 - bands[0] == num_bands


def test_add_coll_with_debt_amount(market, amm, collateral, stable, router, zap, alice):
    stable_amount, coll_amount = amm.get_sum_xy(alice)
    data = router.mockSwap.encode_input(stable, collateral, stable_amount, 2 * 10**18)
    zap.addCollateral(market, 10**18, 2_000 * 10**18, 10, data, {"from": alice})

    assert amm.get_sum_xy(alice) == (0, coll_amount + 3 * 10**18)
    assert market.debt(alice) == 8_000 * 10**18

    assert stable.balanceOf(alice) == 8_000 * 10**18
    assert stable.balanceOf(zap) == 0

    assert collateral.balanceOf(alice) == 4 * 10**18
    assert collateral.balanceOf(zap) == 0


def test_add_coll_partial_swap(market, amm, collateral, stable, router, zap, alice):
    stable_amount, coll_amount = amm.get_sum_xy(alice)
    data = router.mockSwap.encode_input(
        stable, collateral, stable_amount - 1_500 * 10**18, 2 * 10**18
    )
    zap.addCollateral(market, 10**18, 0, 10, data, {"from": alice})

    assert amm.get_sum_xy(alice) == (0, coll_amount + 3 * 10**18)
    assert market.debt(alice) == 8_500 * 10**18

    assert stable.balanceOf(alice) == 10_000 * 10**18
    assert stable.balanceOf(zap) == 0

    assert collateral.balanceOf(alice) == 4 * 10**18
    assert collateral.balanceOf(zap) == 0
