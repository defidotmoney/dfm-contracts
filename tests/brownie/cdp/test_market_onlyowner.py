import brownie


def test_set_amm_fee(market, amm, deployer):
    market.set_amm_fee(10**6, {"from": deployer})
    assert amm.fee() == 10**6


def test_set_amm_admin_fee(market, amm, deployer):
    market.set_amm_admin_fee(123456789, {"from": deployer})
    assert amm.admin_fee() == 123456789


def test_set_borrowing_discounts(market, deployer):
    market.set_borrowing_discounts(5 * 10**17, 10**16, {"from": deployer})
    assert market.loan_discount() == 5 * 10**17
    assert market.liquidation_discount() == 10**16


def test_set_liquidity_mining_hook(market, amm, deployer):
    market.set_liquidity_mining_hook(deployer, {"from": deployer})
    assert amm.lm_hook() == deployer


def test_set_oracle(DummyPriceOracle, market, amm, deployer):
    oracle2 = DummyPriceOracle.deploy(2750 * 10**18, {"from": deployer})
    market.set_oracle(oracle2, {"from": deployer})

    assert amm.ORACLE() == oracle2
    assert amm.price_oracle() == 2750 * 10**18


def test_set_amm_fee_too_high(market, deployer):
    with brownie.reverts("DFM:M Invalid AMM fee"):
        market.set_amm_fee(market.MAX_FEE() + 1, {"from": deployer})


def test_set_amm_fee_too_low(market, deployer):
    with brownie.reverts("DFM:M Invalid AMM fee"):
        market.set_amm_fee(10**6 - 1, {"from": deployer})


def test_set_amm_admin_fee_too_high(market, deployer):
    with brownie.reverts("DFM:M Fee too high"):
        market.set_amm_admin_fee(10**18 + 1, {"from": deployer})


def test_set_borrowing_discounts_liq_above_loan(market, deployer):
    with brownie.reverts("DFM:M loan discount<liq discount"):
        market.set_borrowing_discounts(10**16, 10**17, {"from": deployer})


def test_set_borrowing_discounts_liq_too_low(market, deployer):
    with brownie.reverts("DFM:M liq discount too low"):
        market.set_borrowing_discounts(5 * 10**17, 10**16 - 1, {"from": deployer})


def test_set_borrowing_discounts_loan_too_high(market, deployer):
    with brownie.reverts("DFM:M Loan discount too high"):
        market.set_borrowing_discounts(5 * 10**17 + 1, 10**16, {"from": deployer})


def test_set_oracle_reverts_on_zero_price(DummyPriceOracle, market, amm, deployer):
    oracle2 = DummyPriceOracle.deploy(0, {"from": deployer})
    with brownie.reverts("DFM:M p == 0"):
        market.set_oracle(oracle2, {"from": deployer})
