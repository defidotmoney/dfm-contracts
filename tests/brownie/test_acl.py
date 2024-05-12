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


def test_set_market_hooks(controller, market, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.set_market_hooks(market, [[ZERO_ADDRESS, [False] * 4]], {"from": alice})


def test_set_amm_hook(controller, market, alice):
    with brownie.reverts("DFM:C Only owner"):
        controller.set_amm_hook(market, ZERO_ADDRESS, {"from": alice})


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


# PegKeeper


def test_update(pk, alice):
    with brownie.reverts("DFM:PK Only regulator"):
        pk.update(alice, {"from": alice})


def test_set_new_caller_share(pk, alice):
    with brownie.reverts("DFM:PK Only owner"):
        pk.set_new_caller_share(0, {"from": alice})


def test_set_regulator(pk, regulator, alice):
    with brownie.reverts("DFM:PK Only controller"):
        pk.set_regulator(regulator, {"from": alice})


def test_pk_recall_debt(pk, alice):
    with brownie.reverts("DFM:PK Only regulator"):
        pk.recall_debt(10_000 * 10**18, {"from": alice})


# PegKeeperRegulator


def test_init_migrate_peg_keepers(regulator, alice):
    with brownie.reverts("DFM:R Only controller"):
        regulator.init_migrate_peg_keepers([], [], {"from": alice})


def test_add_peg_keeper(regulator, pk, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.add_peg_keeper(pk, 0, {"from": alice})


def test_remove_peg_keeper(regulator, pk, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.remove_peg_keeper(pk, {"from": alice})


def test_adjust_peg_keeper_debt_ceiling(regulator, pk, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.adjust_peg_keeper_debt_ceiling(pk, 0, {"from": alice})


def test_set_worst_price_threshold(regulator, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.set_worst_price_threshold(0, {"from": alice})


def test_set_price_deviation(regulator, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.set_price_deviation(10**18, {"from": alice})


def test_set_debt_parameters(regulator, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.set_debt_parameters(10**18, 10**18, {"from": alice})


def test_set_killed(regulator, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.set_killed(True, {"from": alice})


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


def test_set_exchange_hook(amm, alice):
    with brownie.reverts("DFM:A Only controller"):
        amm.set_exchange_hook(ZERO_ADDRESS, {"from": alice})
