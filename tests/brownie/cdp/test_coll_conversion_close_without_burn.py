def test_profitable_coll_conversion(
    amm, market, oracle, stable, controller, collateral, alice, bob
):
    LOAN_AMOUNT = 100_000 * 10**18

    # initial mints and approvals
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})
    stable.mint(bob, LOAN_AMOUNT * 4, {"from": controller})
    stable.approve(amm, 2**256 - 1, {"from": bob})

    # alice opens a loan for 100k with 4 bands
    controller.create_loan(alice, market, 50 * 10**18, LOAN_AMOUNT, 4, {"from": alice})

    # zero alice's balance
    stable.transfer(bob, LOAN_AMOUNT, {"from": alice})

    # iterate and adjust the price to the upper bound of each band
    # then bob buys all available collateral at that price
    alice_bands = amm.read_user_tick_numbers(alice)
    for band in range(alice_bands[1], alice_bands[0] - 1, -1):
        price = amm.p_oracle_up(band)
        oracle.set_price(price)
        amm.exchange(0, 1, LOAN_AMOUNT, 0, {"from": bob})

    # alice's loan is now backed only by debt, and the amount exceeds her loan size
    debt, coll = amm.get_sum_xy(alice)
    assert debt > LOAN_AMOUNT
    assert coll == 0

    # alice can now close her loan despite having 0 stable balance
    controller.close_loan(alice, market, {"from": alice})

    # she even makes some money
    assert stable.balanceOf(alice) == debt - LOAN_AMOUNT
