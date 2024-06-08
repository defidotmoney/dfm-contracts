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
    controller = Contract(CONTROLLER)
    token = controller.get_collateral(market)

    amount = Contract(MONEY).balanceOf(account) if use_account_balance else 0
    (debt, coll) = controller.get_close_loan_amounts(account, market)

    assert debt < 0
    assert coll > 0
    shortfall = -(amount + debt)

    assert shortfall > 0

    expected = shortfall / controller.get_oracle_price(token) * (1 + max_slippage)

    received, path_id = get_quote(chain.id, zap, token, MONEY, expected, max_slippage)

    while received < shortfall:
        expected *= shortfall / received
        received, path_id = get_quote(chain.id, zap, token, MONEY, expected, max_slippage)

    return get_route_calldata(zap, path_id)


def get_quote(chain_id, caller, input_token, output_token, amount, max_slippage=0.003):
    if not isinstance(input_token, Contract):
        input_token = Contract(input_token)
    amount = to_int(amount, input_token.decimals())

    quote_request_body = {
        "chainId": chain_id,
        "inputTokens": [
            {"tokenAddress": to_checksum_address(str(input_token)), "amount": str(amount)}
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
