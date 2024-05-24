import boa
import pytest
from math import sqrt, log

PRICE = 3000


@pytest.fixture(scope="module")
def borrowed_token(get_borrowed_token):
    return get_borrowed_token(6)


@pytest.fixture(scope="module")
def get_amm(price_oracle, admin, accounts):
    def f(collateral_token, borrowed_token):
        with boa.env.prank(admin):
            amm = boa.load(
                "contracts/cdp/AMM.vy",
                admin,
                borrowed_token,
                100,
            )
            amm.initialize(
                admin,
                price_oracle,
                collateral_token,
                PRICE * 10**18,
                10**16,
                0,
            )
            # amm.set_admin(admin)
        for acct in accounts:
            with boa.env.prank(acct):
                collateral_token.approve(amm.address, 2**256 - 1)
                borrowed_token.approve(amm.address, 2**256 - 1)
        return amm

    return f


@pytest.fixture(scope="module")
def amm(collateral_token, borrowed_token, get_amm):
    return get_amm(collateral_token, borrowed_token)
