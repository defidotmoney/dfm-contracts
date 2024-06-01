import pytest
import brownie
from brownie import ZERO_ADDRESS

market_A = 100
market_fee = 6 * 10**15  # 0.6%
market_admin_fee = 5 * 10**17  # 50% of the market fee
market_loan_discount = 9 * 10**16  # 9%; +2% from 4x 1% bands = 100% - 11% = 89% LTV
market_liquidation_discount = 6 * 10**16  # 6%
market_debt_cap = 10_000_000 * 10**18


def test_add_market(
    MarketOperator, AMM, core, controller, collateral, oracle, policy, stable, deployer
):
    controller.add_market(
        collateral,
        market_A,
        market_fee,
        market_admin_fee,
        oracle,
        0,
        market_loan_discount,
        market_liquidation_discount,
        market_debt_cap,
        {"from": deployer},
    )

    market = MarketOperator.at(controller.get_market(collateral))
    amm = AMM.at(controller.get_amm(collateral))

    assert controller.market_contracts(market).dict() == {
        "collateral": collateral,
        "amm": amm,
        "mp_idx": 0,
    }
    assert controller.get_monetary_policy_for_market(market) == policy

    assert market.CORE_OWNER() == core
    assert market.owner() == core.owner()
    assert market.CONTROLLER() == controller
    assert market.AMM() == amm
    assert market.debt_ceiling() == market_debt_cap
    assert market.liquidation_discount() == market_liquidation_discount
    assert market.loan_discount() == market_loan_discount
    assert market.MAX_FEE() == market.MIN_TICKS() * 10**18 // market_A > 0

    assert amm.coins(0) == stable
    assert amm.coins(1) == collateral
    assert amm.ORACLE() == oracle
    assert amm.MARKET_OPERATOR() == market
    assert amm.A() == market_A
    assert amm.fee() == market_fee
    assert amm.admin_fee() == market_admin_fee

    assert collateral.allowance(amm, controller) == 2**256 - 1
    assert stable.allowance(amm, controller) == 2**256 - 1

    assert collateral.allowance(amm, market) == 0
    assert stable.allowance(amm, market) == 0


def test_wrong_A(controller, collateral, oracle, deployer):
    with brownie.reverts("DFM:C No implementation for A"):
        controller.add_market(
            collateral,
            69,
            market_fee,
            market_admin_fee,
            oracle,
            0,
            market_loan_discount,
            market_liquidation_discount,
            market_debt_cap,
            {"from": deployer},
        )


def test_high_fee(controller, collateral, oracle, deployer):
    with brownie.reverts("DFM:C Fee too high"):
        controller.add_market(
            collateral,
            market_A,
            10**17 + 1,
            market_admin_fee,
            oracle,
            0,
            market_loan_discount,
            market_liquidation_discount,
            market_debt_cap,
            {"from": deployer},
        )


def test_low_fee(controller, collateral, oracle, deployer):
    with brownie.reverts("DFM:C Fee too low"):
        controller.add_market(
            collateral,
            market_A,
            10**6 - 1,
            market_admin_fee,
            oracle,
            0,
            market_loan_discount,
            market_liquidation_discount,
            market_debt_cap,
            {"from": deployer},
        )


def test_high_admin_fee(controller, collateral, oracle, deployer):
    with brownie.reverts("DFM:C Admin fee too high"):
        controller.add_market(
            collateral,
            market_A,
            market_fee,
            10**18 + 1,
            oracle,
            0,
            market_loan_discount,
            market_liquidation_discount,
            market_debt_cap,
            {"from": deployer},
        )


def test_low_liquidation_discount(controller, collateral, oracle, deployer):
    with brownie.reverts("DFM:C liq discount too low"):
        controller.add_market(
            collateral,
            market_A,
            market_fee,
            market_admin_fee,
            oracle,
            0,
            market_loan_discount,
            10**16 - 1,
            market_debt_cap,
            {"from": deployer},
        )


def test_high_loan_discount(controller, collateral, oracle, deployer):
    with brownie.reverts("DFM:C Loan discount too high"):
        controller.add_market(
            collateral,
            market_A,
            market_fee,
            market_admin_fee,
            oracle,
            0,
            5 * 10**17 + 1,
            market_liquidation_discount,
            market_debt_cap,
            {"from": deployer},
        )


def test_loan_gt_liq(controller, collateral, oracle, deployer):
    with brownie.reverts("DFM:C loan discount<liq discount"):
        controller.add_market(
            collateral,
            market_A,
            market_fee,
            market_admin_fee,
            oracle,
            0,
            market_liquidation_discount - 1,
            market_liquidation_discount,
            market_debt_cap,
            {"from": deployer},
        )


def test_invalid_mp_idx(controller, collateral, oracle, deployer):
    with brownie.reverts("DFM:C invalid mp_idx"):
        controller.add_market(
            collateral,
            market_A,
            market_fee,
            market_admin_fee,
            oracle,
            1,
            market_loan_discount,
            market_liquidation_discount,
            market_debt_cap,
            {"from": deployer},
        )


def test_oracle_price_zero(controller, collateral, oracle, deployer):
    oracle.set_price(0, {"from": deployer})
    with brownie.reverts("DFM:C p == 0"):
        controller.add_market(
            collateral,
            market_A,
            market_fee,
            market_admin_fee,
            oracle,
            0,
            market_loan_discount,
            market_liquidation_discount,
            market_debt_cap,
            {"from": deployer},
        )


@pytest.mark.parametrize("bad_A", [1, 10001])
def test_set_impl_wrong_A(controller, market, amm, deployer, bad_A):
    with brownie.reverts("DFM:C A outside bounds"):
        controller.set_implementations(bad_A, market, amm, {"from": deployer})


def test_set_impl_matching_impls(controller, market, deployer):
    with brownie.reverts("DFM:C matching implementations"):
        controller.set_implementations(50, market, market, {"from": deployer})


def test_set_impl_empty_amm(controller, market, deployer):
    with brownie.reverts("DFM:C empty implementation"):
        controller.set_implementations(50, market, ZERO_ADDRESS, {"from": deployer})


def test_set_impl_empty_market(controller, amm, deployer):
    with brownie.reverts("DFM:C empty implementation"):
        controller.set_implementations(50, ZERO_ADDRESS, amm, {"from": deployer})


def test_set_impl_clear(controller, collateral, oracle, deployer):
    assert controller.get_implementations(100)[0] != ZERO_ADDRESS
    assert controller.get_implementations(100)[1] != ZERO_ADDRESS
    controller.set_implementations(100, ZERO_ADDRESS, ZERO_ADDRESS, {"from": deployer})
    assert controller.get_implementations(100) == [ZERO_ADDRESS, ZERO_ADDRESS]
    with brownie.reverts("DFM:C No implementation for A"):
        controller.add_market(
            collateral,
            100,
            market_fee,
            market_admin_fee,
            oracle,
            0,
            market_loan_discount,
            market_liquidation_discount,
            market_debt_cap,
            {"from": deployer},
        )


def test_set_impl_wrong_A_amm(MarketOperator, AMM, core, stable, controller, deployer):
    market_impl = MarketOperator.deploy(core, controller, 100, {"from": deployer})
    amm_impl = AMM.deploy(controller, stable, 69, {"from": deployer})

    with brownie.reverts("DFM:C incorrect amm A"):
        controller.set_implementations(100, market_impl, amm_impl, {"from": deployer})


def test_set_impl_wrong_A_market(MarketOperator, AMM, core, stable, controller, deployer):
    market_impl = MarketOperator.deploy(core, controller, 420, {"from": deployer})
    amm_impl = AMM.deploy(controller, stable, 100, {"from": deployer})

    with brownie.reverts("DFM:C incorrect market A"):
        controller.set_implementations(100, market_impl, amm_impl, {"from": deployer})
