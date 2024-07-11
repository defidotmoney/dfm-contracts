import os
from datetime import timedelta
from math import log
from typing import Any, Callable

import boa
import pytest
from hypothesis import settings, Phase


PRICE = 3000


settings.register_profile("default", deadline=timedelta(seconds=1000))
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


def approx(x1: int, x2: int, precision: int, abs_precision=None):
    if precision >= 1:
        return True
    result = False
    if abs_precision is not None:
        result = abs(x2 - x1) <= abs_precision
    else:
        abs_precision = 0
    if x2 == 0:
        return abs(x1) <= abs_precision
    elif x1 == 0:
        return abs(x2) <= abs_precision
    return result or (abs(log(x1 / x2)) <= precision)


@pytest.fixture(scope="session")
def accounts():
    return [boa.env.generate_address() for _ in range(10)]


@pytest.fixture(scope="session")
def admin():
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def fee_receiver():
    return "000000000000000000000000000000000000fee5"


@pytest.fixture(scope="session")
def get_collateral_token(admin) -> Callable[[int], Any]:
    def f(digits):
        with boa.env.prank(admin):
            return boa.load("contracts/testing/ERC20Mock.vy", "Colalteral", "ETH", digits)

    return f


@pytest.fixture(scope="session")
def get_borrowed_token(admin) -> Callable[[int], Any]:
    def f(digits):
        with boa.env.prank(admin):
            return boa.load("contracts/testing/ERC20Mock.vy", "Rugworks USD", "rUSD", digits)

    return f


@pytest.fixture(scope="module")
def collateral_token(get_collateral_token):
    return get_collateral_token(18)


@pytest.fixture(scope="module")
def price_oracle(admin):
    with boa.env.prank(admin):
        oracle = boa.load("contracts/testing/PriceOracleMock.vy", PRICE * 10**18)
        return oracle


@pytest.fixture(scope="module")
def core(admin, fee_receiver):
    with boa.env.prank(admin):
        return boa.load("contracts/testing/CoreOwnerMock.vy", admin, fee_receiver)


@pytest.fixture(scope="module")
def stablecoin(admin):
    with boa.env.prank(admin):
        return boa.load("contracts/testing/ERC20Mock.vy", "Curve USD", "crvUSD", 18)


@pytest.fixture(scope="module")
def operator_interface():
    return boa.load_partial("contracts/cdp/MarketOperator.vy")


@pytest.fixture(scope="module")
def amm_interface():
    return boa.load_partial("contracts/cdp/AMM.vy")


@pytest.fixture(scope="module")
def controller(core, stablecoin, admin, monetary_policy):
    with boa.env.prank(admin):
        contract = boa.load(
            "contracts/cdp/MainController.vy",
            core.address,
            stablecoin.address,
            [monetary_policy.address],
            2**256 - 1,
        )
        stablecoin.setMinter(contract.address, True)
        operator_impl = boa.load("contracts/cdp/MarketOperator.vy", core, contract, 100)
        amm_impl = boa.load("contracts/cdp/AMM.vy", contract, stablecoin, 100)
        contract.set_implementations(100, operator_impl, amm_impl)
    return contract


@pytest.fixture(scope="module")
def monetary_policy(admin):
    with boa.env.prank(admin):
        policy = boa.load("contracts/testing/ConstantMonetaryPolicy.vy", admin)
        policy.set_rate(0)
        return policy


@pytest.fixture(scope="module")
def market(
    admin, controller, price_oracle, accounts, stablecoin, operator_interface, collateral_token
):
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
            10**6 * 10**18,
        )
        amm = controller.get_amm(collateral_token.address)
        market = controller.get_market(collateral_token.address)
        for acc in accounts:
            with boa.env.prank(acc):
                collateral_token.approve(amm, 2**256 - 1)
                stablecoin.approve(amm, 2**256 - 1)
                collateral_token.approve(controller, 2**256 - 1)
                stablecoin.approve(controller, 2**256 - 1)
        return operator_interface.at(market)


@pytest.fixture(scope="module")
def amm(market, collateral_token, amm_interface, controller):
    return amm_interface.at(controller.get_amm(collateral_token.address))
