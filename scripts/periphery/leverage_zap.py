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
    token = Contract(controller.get_collateral(market))

    amount = Contract(MONEY).balanceOf(account) if use_account_balance else 0
    (debt, coll) = controller.get_close_loan_amounts(account, market)

    assert debt < 0
    assert coll > 0
    shortfall = -(amount + debt)

    assert shortfall > 0

    amount_out = shortfall / controller.get_oracle_price(token) * (1 + max_slippage)
    amount_out = to_int(amount_out, token.decimals())

    amount_in, path_id = odos.get_quote(chain.id, zap, token, MONEY, amount_out, max_slippage)

    while amount_in < shortfall:
        amount_out = int(amount_out * shortfall / amount_in)
        amount_in, path_id = odos.get_quote(chain.id, zap, token, MONEY, amount_out, max_slippage)

    return odos.get_route_calldata(zap, path_id), amount_out, amount_in


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
    token, amm = controller.market_contracts(market)[:-1]

    debt_amm, coll_amm = Contract(amm).get_sum_xy(account)
    assert debt_amm > 0

    received, path_id = odos.get_quote(chain.id, zap, MONEY, token, debt_amm, max_slippage)

    return odos.get_route_calldata(zap, path_id), coll_amount + coll_amm + received
