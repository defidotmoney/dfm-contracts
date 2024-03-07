import boa


def test_impl(controller, operator_impl, amm_impl):
    assert controller.market_operator_implementation() == operator_impl.address
    assert controller.amm_implementation() == amm_impl.address


def test_add_market(
    controller,
    collateral_token,
    price_oracle,
    monetary_policy,
    admin,
    operator_interface,
    amm_interface,
):
    # token: address, A: uint256, fee: uint256, admin_fee: uint256,
    # _price_oracle_contract: address,
    # monetary_policy: address, loan_discount: uint256, liquidation_discount: uint256,
    # debt_ceiling: uint256) -> address[2]:
    with boa.env.anchor():
        with boa.env.prank(admin):
            controller.add_market(
                collateral_token.address,
                100,
                10**16,
                0,
                price_oracle.address,
                0,
                5 * 10**16,
                2 * 10**16,
                10**8 * 10**18,
            )

            assert controller.n_collaterals() == 1
            assert controller.collaterals(0).lower() == collateral_token.address.lower()

            market = operator_interface.at(controller.get_market(collateral_token.address))
            amm = amm_interface.at(controller.get_amm(collateral_token.address))

            assert market.CONTROLLER().lower() == controller.address.lower()
            assert market.collateral_token().lower() == collateral_token.address.lower()
            assert market.AMM().lower() == amm.address.lower()
            assert (
                controller.get_monetary_policy_for_market(market.address).lower()
                == monetary_policy.address.lower()
            )
            assert market.liquidation_discount() == 2 * 10**16
            assert market.loan_discount() == 5 * 10**16
            assert market.debt_ceiling() == 10**8 * 10**18

            assert amm.A() == 100
            assert amm.price_oracle_contract().lower() == price_oracle.address.lower()
            assert amm.coins(1).lower() == collateral_token.address.lower()
