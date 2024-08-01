import requests
from web3.main import to_checksum_address

from brownie import Contract, chain
from scripts.utils.float2int import to_int

# https://docs.odos.xyz/api/endpoints/
QUOTE_URL = "https://api.odos.xyz/sor/quote/v2"
ASSEMBLE_URL = "https://api.odos.xyz/sor/assemble"

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
    amount_out = to_int(amount, token.decimals())

    amount_in, path_id = get_quote(chain.id, zap, token, MONEY, amount_out, max_slippage)

    while amount_in < shortfall:
        amount_out = int(amount_out * shortfall / amount_in)
        amount_in, path_id = get_quote(chain.id, zap, token, MONEY, amount_out, max_slippage)

    return get_route_calldata(zap, path_id), amount_out, amount_in


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

    received, path_id = get_quote(chain.id, zap, MONEY, token, debt_amm, max_slippage)

    return get_route_calldata(zap, path_id), coll_amount + coll_amm + received


def get_quote(chain_id, caller, input_token, output_token, amount_in, max_slippage=0.003):
    """
    Args:
        amount_in: Amount of input_token being swapped, as an integer with the same precision
            used in the token smart contract
    """
    quote_request_body = {
        "chainId": chain_id,
        "inputTokens": [
            {"tokenAddress": to_checksum_address(str(input_token)), "amount": str(amount_in)}
        ],
        "outputTokens": [{"tokenAddress": to_checksum_address(str(output_token)), "proportion": 1}],
        "slippageLimitPercent": max_slippage * 100,
        "userAddr": to_checksum_address(str(caller)),
        "referralCode": 0,
        "disableRFQs": True,
        "compact": True,
    }

    response = requests.post(
        QUOTE_URL,
        headers={"Content-Type": "application/json"},
        json=quote_request_body,
    )

    if response.status_code != 200:
        raise ValueError(f"{response.status_code} error during quote: {response.json()}")

    quote = response.json()

    return int(quote["outAmounts"][0]), quote["pathId"]


def get_route_calldata(caller, path_id):
    assemble_request_body = {
        "userAddr": to_checksum_address(str(caller)),
        "pathId": path_id,
        "simulate": False,
    }

    response = requests.post(
        ASSEMBLE_URL,
        headers={"Content-Type": "application/json"},
        json=assemble_request_body,
    )

    if response.status_code != 200:
        raise ValueError(f"{response.status_code} error during assembly: {response.json()}")

    data = response.json()

    return data["transaction"]["data"]
