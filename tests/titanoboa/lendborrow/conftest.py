import boa
import pytest
from vyper.utils import method_id


def get_method_id(desc):
    return method_id(desc).to_bytes(4, "big") + b"\x00" * 28


@pytest.fixture(scope="module")
def core(admin):
    with boa.env.prank(admin):
        return boa.load("contracts/testing/CoreOwner.vy")


@pytest.fixture(scope="module")
def stablecoin(admin):
    with boa.env.prank(admin):
        return boa.load("contracts/testing/ERC20Mock.vy", "Curve USD", "crvUSD", 18)


@pytest.fixture(scope="module")
def operator_interface():
    return boa.load_partial("contracts/MarketOperator.vy")


@pytest.fixture(scope="module")
def operator_impl(operator_interface, admin):
    with boa.env.prank(admin):
        return operator_interface.deploy_as_blueprint()


@pytest.fixture(scope="module")
def amm_interface():
    return boa.load_partial("contracts/AMM.vy")


@pytest.fixture(scope="module")
def amm_impl(stablecoin, amm_interface, admin):
    with boa.env.prank(admin):
        return amm_interface.deploy_as_blueprint()


@pytest.fixture(scope="module")
def controller(core, amm_impl, operator_impl, stablecoin, admin, accounts, monetary_policy):
    with boa.env.prank(admin):
        contract = boa.load(
            "contracts/MainController.vy",
            core.address,
            stablecoin.address,
            operator_impl,
            amm_impl,
            [monetary_policy.address],
        )
        stablecoin.setMinter(contract.address, True)
    return contract


@pytest.fixture(scope="module")
def monetary_policy(admin):
    with boa.env.prank(admin):
        policy = boa.load("contracts/testing/ConstantMonetaryPolicy.vy", admin)
        policy.set_rate(0)
        return policy


@pytest.fixture(scope="module")
def get_market(controller, price_oracle, stablecoin, accounts, admin):
    def f(collateral_token):
        with boa.env.prank(admin):
            if controller.n_collaterals() == 0:
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
            return market

    return f


@pytest.fixture(scope="module")
def market(operator_interface, get_market, collateral_token):
    contract = get_market(collateral_token)
    return operator_interface.at(contract)


@pytest.fixture(scope="module")
def amm(market, collateral_token, stablecoin, amm_interface, controller):
    return amm_interface.at(controller.get_amm(collateral_token.address))


@pytest.fixture(scope="module")
def get_fake_leverage(stablecoin, admin):
    raise NotImplemented

    def f(collateral_token, market_controller):
        # Fake leverage testing contract can also be used to liquidate via the callback
        with boa.env.prank(admin):
            leverage = boa.load(
                "contracts/testing/FakeLeverage.vy",
                stablecoin.address,
                collateral_token.address,
                market_controller.address,
                3000 * 10**18,
            )
            collateral_token._mint_for_testing(
                leverage.address, 1000 * 10 ** collateral_token.decimals()
            )
            return leverage

    return f


@pytest.fixture(scope="module")
def fake_leverage(get_fake_leverage, collateral_token, market_controller):
    return get_fake_leverage(collateral_token, market_controller)


@pytest.fixture(scope="module")
def fee_receiver(core, admin):
    addr = "0x1234123412341234123412341234123412341234"
    with boa.env.prank(admin):
        core.setFeeReceiver(addr)
    return addr
