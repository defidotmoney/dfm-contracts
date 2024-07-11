import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(collateral, controller, alice):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})


def test_increase_hook_debt_does_not_affect_fees(
    market, hooks, stable, fee_receiver, controller, alice, deployer
):
    # test verifies a fix of finding CS-DFM-031 within ChainSecurity audit

    # + 500 to minted and redeemed
    controller.create_loan(alice, market, 10**18, 500, 5, {"from": alice})
    controller.close_loan(alice, market, {"from": alice})

    # use a debt-only hook to mint 500 while increasing debt by 1500 total
    hooks.set_response(1000, {"from": alice})
    hooks.set_configuration(1, [True, True, False, False], {"from": deployer})
    controller.add_market_hook(market, hooks, {"from": deployer})
    controller.create_loan(alice, market, 10**18, 500, 5, {"from": alice})

    # assert initial test conditions
    assert controller.total_debt() == 1500
    assert controller.redeemed() == 500
    assert controller.minted() == 1000
    assert controller.total_hook_debt() == 0

    # 1500 + 500 - 1000 - 0
    assert controller.stored_admin_fees() == 1000

    # adjust hook to be debt+rebate
    controller.remove_market_hook(market, hooks, {"from": deployer})
    hooks.set_configuration(2, [False, True, False, False], {"from": deployer})
    controller.add_market_hook(market, hooks, {"from": deployer})

    # alice increases the hook debt by 200
    controller.increase_hook_debt(market, hooks, 200, {"from": alice})

    # now the hook gives a rebate of 200 when alice adjusts her loan
    hooks.set_response(-200, {"from": alice})
    controller.adjust_loan(alice, market, 0, -100, {"from": alice})

    # protocol fees should be unaffected by alice's actions
    assert controller.stored_admin_fees() == 1000
    controller.collect_fees([market], {"from": alice})
    assert stable.balanceOf(fee_receiver) == 1000
