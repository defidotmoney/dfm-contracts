import brownie
from brownie import ZERO_ADDRESS


# MainController


def test_add_market(controller, collateral, oracle, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.add_market(collateral, 200, 600000, 0, oracle, 0, 0, 0, 0, {"from": alice})


def test_set_global_market_debt_ceiling(controller, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.set_global_market_debt_ceiling(0, {"from": alice})


def test_set_implementations(controller, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.set_implementations(100, ZERO_ADDRESS, ZERO_ADDRESS, {"from": alice})


def test_add_market_hook(controller, market, hooks, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.add_market_hook(market, hooks, {"from": alice})


def test_remove_market_hook(controller, market, hooks, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.remove_market_hook(market, hooks, {"from": alice})


def test_add_new_monetary_policy(controller, policy, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.add_new_monetary_policy(policy, {"from": alice})


def test_change_existing_monetary_policy(controller, policy, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.change_existing_monetary_policy(policy, 0, {"from": alice})


def test_change_market_monetary_policy(controller, market, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.change_market_monetary_policy(market, 0, {"from": alice})


def test_set_peg_keeper_regulator(controller, regulator, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.set_peg_keeper_regulator(regulator, False, {"from": alice})


# MarketOperator


def test_set_amm_fee(market, alice):
    with brownie.reverts("DFM:M Only owner"):
        market.set_amm_fee(0, {"from": alice})


def test_set_amm_admin_fee(market, alice):
    with brownie.reverts("DFM:M Only owner"):
        market.set_amm_admin_fee(0, {"from": alice})


def test_set_borrowing_discounts(market, alice):
    with brownie.reverts("DFM:M Only owner"):
        market.set_borrowing_discounts(10**16, 5 * 10**17, {"from": alice})


def test_set_liquidity_mining_hook(market, alice):
    with brownie.reverts("DFM:M Only owner"):
        market.set_liquidity_mining_hook(ZERO_ADDRESS, {"from": alice})


def test_set_debt_ceiling(market, alice):
    with brownie.reverts("DFM:M Only owner"):
        market.set_debt_ceiling(0, {"from": alice})


def test_create_loan(market, alice):
    with brownie.reverts("DFM:M Only controller"):
        market.create_loan(alice, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})


def test_adjust_loan(market, alice):
    with brownie.reverts("DFM:M Only controller"):
        market.adjust_loan(alice, 0, 1000 * 10**18, 10, {"from": alice})


def test_close_loan(market, alice):
    with brownie.reverts("DFM:M Only controller"):
        market.close_loan(alice, {"from": alice})


def test_liquidate(market, alice):
    with brownie.reverts("DFM:M Only controller"):
        market.liquidate(alice, alice, 0, 10**18, {"from": alice})


def test_collect_fees(market, alice):
    with brownie.reverts("DFM:M Only controller"):
        market.collect_fees({"from": alice})


# AMM


def test_deposit_range(amm, alice):
    with brownie.reverts("DFM:A Only operator"):
        amm.deposit_range(alice, 10_000 * 10**18, 1, 10, {"from": alice})


def test_withdraw(amm, alice):
    with brownie.reverts("DFM:A Only operator"):
        amm.withdraw(alice, 10**18, {"from": alice})


def test_amm_set_fee(amm, alice):
    with brownie.reverts("DFM:A Only operator"):
        amm.set_fee(0, {"from": alice})


def test_amm_set_admin_fee(amm, alice):
    with brownie.reverts("DFM:A Only operator"):
        amm.set_admin_fee(0, {"from": alice})


def test_reset_admin_fees(amm, alice):
    with brownie.reverts("DFM:A Only operator"):
        amm.reset_admin_fees({"from": alice})


def test_set_liquidity_mining_hook(amm, alice):
    with brownie.reverts("DFM:A Only operator"):
        amm.set_liquidity_mining_hook(ZERO_ADDRESS, {"from": alice})


def test_set_rate(amm, alice):
    with brownie.reverts("DFM:A Only controller"):
        amm.set_rate(0, {"from": alice})
