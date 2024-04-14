import pytest
import brownie

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
    assert market.STABLECOIN() == stable
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


@pytest.mark.parametrize("bad_A", [1, 10001])
def test_wrong_A(controller, collateral, oracle, deployer, bad_A):
    with brownie.reverts("DFM:C Wrong A"):
        controller.add_market(
            collateral,
            bad_A,
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
