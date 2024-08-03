from brownie import Contract, chain
from scripts.utils.float2int import to_int
from .utils import odos


CONTROLLER = "0x1337F001E280420EcCe9E7B934Fa07D67fdb62CD"
MONEY = "0x69420f9e38a4e60a62224c489be4bf7a94402496"


def get_create_loan_routing_data(zap, account, market, coll_amount, debt_amount):
    # TODO
    pass


def get_increase_loan_routing_data(zap, account, market, coll_amount, debt_amount):
    # TODO
    pass


def get_decrease_loan_routing_data(zap, account, market, coll_amount, debt_amount):
    # TODO
    pass


def get_close_loan_routing_data(zap, account, market, use_account_balance=True, max_slippage=0.003):
    """
    Generates the `routingData` input for use with `LeverageZap.closeLoan`.

    Note that Odos' quotes are valid for 60 seconds, if the generated data is not used within
    that timeframe it will need to be re-queried.

    Args:
        zap: Address of `LeverageZap` deployment on the connected chain
        account: Address of the account that will close a loan
        market: Address of the market where the loan is being closed
        use_account_balance: If True, the full MONEY balance of `account` is used and the zap
            only swaps enough collateral to cover the difference. If False, no MONEY is taken
            from `account` and the zap will swap enough collateral to cover the entire debt.
        max_slippage: Maximum allowable slippage in the router swap, denoted as a fraction.
            Excess MONEY from the swap is returned to the caller. Setting slippage too low
            will fail because of interest that accrues between the time of generating the
            swap data and the time the transaction confirms.

    Returns:
        string: `routingData` for use in `LeverageZap.closeLoan`
        int: Amount of collateral that will be swapped for MONEY, as an integer with the same
             precision used in the token smart contract
        int: Expected amount of MONEY received in the swap, as an integer with 1e18 precision
    """
    controller = Contract(CONTROLLER)
    collateral = Contract(controller.get_collateral(market))

    amount = Contract(MONEY).balanceOf(account) if use_account_balance else 0
    (debt_amm, coll_amm) = controller.get_close_loan_amounts(account, market)
    debt_shortfall = -(amount + debt_amm)

    assert debt_amm < 0
    assert coll_amm > 0
    assert debt_shortfall > 0

    # need to swap an amount of collateral (`amount_in`) for an exact amount of debt (`debt_shortfall`)
    # but Odos' API does not provide quotes based on an exact amount out

    # estimate required `amount_in` based on our exact `amount_out`
    amount_in = debt_shortfall / controller.get_oracle_price(collateral) * (1 + max_slippage)
    amount_in = to_int(amount_in, collateral.decimals())
    amount_out, path_id = odos.get_quote(chain.id, zap, collateral, MONEY, amount_in, max_slippage)

    # increase `amount_in` until we find a quote that gives sufficient `amount_out`
    while amount_out < debt_shortfall:
        amount_in = int(amount_in * debt_shortfall / amount_out)
        amount_out, path_id = odos.get_quote(
            chain.id, zap, collateral, MONEY, amount_in, max_slippage
        )

    return odos.get_route_calldata(zap, path_id), amount_in, amount_out


def get_add_coll_routing_data(zap, account, market, coll_amount, max_slippage=0.003):
    """
    Generates the `routingData` input for use with `LeverageZap.addCollateral`.

    Note that Odos' quotes are valid for 60 seconds, if the generated data is not used within
    that timeframe it will need to be re-queried.

    Args:
        zap: Address of `LeverageZap` deployment on the connected chain
        account: Address of the account that will adjust a loan
        market: Address of the market where the loan is being adjusted
        coll_amount: Amount of collateral being added to the loan by `account`. Note that
            this value does not affect the routing data, it is only used in calculating
            the return value.
        max_slippage: Maximum allowable slippage in the router swap, denoted as a fraction.

    Returns:
        string: `routingData` for use in `LeverageZap.closeLoan`
        int: New collateral balance that will be backing the loan, as an integer with
             the same precision used in the token smart contract
    """
    controller = Contract(CONTROLLER)
    collateral, amm = controller.market_contracts(market)[:-1]

    debt_amm, coll_amm = Contract(amm).get_sum_xy(account)

    assert debt_amm > 0

    # generate quote to swap exactly `debt_amm` of MONEY into an amount of `collateral`
    received, path_id = odos.get_quote(chain.id, zap, MONEY, collateral, debt_amm, max_slippage)

    return odos.get_route_calldata(zap, path_id), coll_amount + coll_amm + received
