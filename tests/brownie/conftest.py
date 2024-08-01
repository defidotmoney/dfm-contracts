import pytest
from brownie_tokens import ERC20


MARKET_DEBT_CAP = 10_000_000 * 10**18
MARKET_A = 100
market_fee = 6 * 10**15  # 0.6%
market_admin_fee = 5 * 10**17  # 50% of the market fee
market_loan_discount = 9 * 10**16  # 9%; +2% from 4x 1% bands = 100% - 11% = 89% LTV
market_liquidation_discount = 6 * 10**16  # 6%


@pytest.fixture(scope="function", autouse=True)
def base_setup(fn_isolation):
    pass


@pytest.fixture(scope="module")
def deployer(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def guardian(accounts, core, deployer):
    key = b"GUARDIAN".ljust(32, b"\x00")
    core.setAddress(key, accounts[1], {"from": deployer})
    return accounts[1]


@pytest.fixture(scope="module")
def alice(accounts):
    return accounts[2]


@pytest.fixture(scope="module")
def bob(accounts):
    return accounts[3]


@pytest.fixture(scope="module")
def fee_receiver():
    return "000000000000000000000000000000000000fee5"


@pytest.fixture(scope="module")
def core(DFMProtocolCore, deployer, fee_receiver):
    return DFMProtocolCore.deploy(deployer, fee_receiver, 0, {"from": deployer})


@pytest.fixture(scope="module")
def stable(BridgeToken, LzEndpointMock, core, deployer):
    mock_endpoint = LzEndpointMock.deploy({"from": deployer})
    return BridgeToken.deploy(core, "Stablecoin", "SC", mock_endpoint, b"", [], {"from": deployer})


@pytest.fixture(scope="module")
def policy(ConstantMonetaryPolicy, deployer):
    return ConstantMonetaryPolicy.deploy({"from": deployer})


@pytest.fixture(scope="module")
def dummy_oracle(PriceOracleMock, deployer):
    return PriceOracleMock.deploy(3000 * 10**18, {"from": deployer})


@pytest.fixture(scope="module")
def agg_stable(AggregateStablePrice, core, stable, deployer):
    return AggregateStablePrice.deploy(core, stable, 10**15, {"from": deployer})


@pytest.fixture(scope="module")
def controller(MainController, MarketOperator, AMM, core, stable, policy, deployer):
    contract = MainController.deploy(core, stable, [policy], 2**256 - 1, {"from": deployer})
    stable.setMinter(contract, True, {"from": deployer})

    market_impl = MarketOperator.deploy(core, contract, MARKET_A, {"from": deployer})
    amm_impl = AMM.deploy(contract, stable, MARKET_A, {"from": deployer})
    contract.set_implementations(MARKET_A, market_impl, amm_impl, {"from": deployer})

    return contract


@pytest.fixture(scope="module")
def collateral():
    return ERC20(success=True, fail="revert")


@pytest.fixture(scope="module")
def collateral2():
    return ERC20(success=None, fail="revert")


@pytest.fixture(scope="module")
def collateral3():
    return ERC20(success=True, fail=False)


@pytest.fixture(scope="module")
def collateral_list(collateral, collateral2, collateral3):
    return [collateral, collateral2, collateral3]


@pytest.fixture(scope="module")
def _deploy_market(MarketOperator, controller, dummy_oracle, deployer):
    def fn(collateral):
        controller.add_market(
            collateral,
            MARKET_A,
            market_fee,
            market_admin_fee,
            dummy_oracle,
            0,
            market_loan_discount,
            market_liquidation_discount,
            MARKET_DEBT_CAP,
            {"from": deployer},
        )
        return MarketOperator.at(controller.get_market(collateral))

    return fn


@pytest.fixture(scope="module")
def market(_deploy_market, collateral):
    return _deploy_market(collateral)


@pytest.fixture(scope="module")
def amm(AMM, controller, market):
    return AMM.at(controller.market_contracts(market)["amm"])


@pytest.fixture(scope="module")
def views(MarketViews, controller, deployer):
    return MarketViews.deploy(controller, {"from": deployer})


@pytest.fixture(scope="module")
def eth_receive_reverter(EthReceiveTester, deployer):
    # can be used to send ETH to payable functions
    # will revert if the contract attempts to send any ETH back
    contract = EthReceiveTester.deploy({"from": deployer})
    contract.receive_eth({"from": deployer, "value": "1 ether"})
    return contract
