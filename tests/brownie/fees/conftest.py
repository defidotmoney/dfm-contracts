import pytest


SWAP_BONUS_PCT = 100
MAX_SWAP_BONUS = 50000
MIN_RELAY_BALANCE = 10**10
MAX_RELAY_SWAP_DEBT = 50000
PRIMARY_ID = 101
BRIDGE_BONUS_PCT = 100
MAX_BRIDGE_BONUS = 1000
FEE_AGG_CALLER_INCENTIVE = 100
COOLDOWN_PERIOD = 7 * 76400

REG_MIN_PRICE = int(0.99 * 10**18)
REG_MAX_PRICE = int(1.01 * 10**18)
REG_MIN_STAKER_PCT = 3000
REG_MAX_STAKER_PCT = 7000


@pytest.fixture(scope="session")
def relay_key():
    return "BRIDGE_RELAY".encode().hex().ljust(64, "0")


@pytest.fixture(scope="module")
def weth(collateral):
    return collateral


@pytest.fixture(scope="module")
def converter_primary(FeeConverter, core, controller, stable, weth, fee_agg, deployer):
    return FeeConverter.deploy(
        core,
        controller,
        stable,
        fee_agg,
        weth,
        SWAP_BONUS_PCT,
        MAX_SWAP_BONUS,
        MIN_RELAY_BALANCE,
        MAX_RELAY_SWAP_DEBT,
        {"from": deployer},
    )


@pytest.fixture(scope="module")
def converter_bridge(FeeConverterWithBridge, core, controller, stable, weth, fee_agg, deployer):
    return FeeConverterWithBridge.deploy(
        core,
        controller,
        stable,
        fee_agg,
        weth,
        SWAP_BONUS_PCT,
        MAX_SWAP_BONUS,
        MIN_RELAY_BALANCE,
        MAX_RELAY_SWAP_DEBT,
        PRIMARY_ID,
        BRIDGE_BONUS_PCT,
        MAX_BRIDGE_BONUS,
        {"from": deployer},
    )


# parametrized fixture runs tests against both `FeeConverter` and `FeeConverterWithBridge`
# used to test common base functions inherited from `FeeConverterBase`
@pytest.fixture(scope="module", params=["primary", "bridge"])
def converter(converter_primary, converter_bridge, request):
    if request.param == "primary":
        return converter_primary
    else:
        return converter_bridge


@pytest.fixture(scope="module")
def fee_agg(PrimaryFeeAggregator, core, stable, deployer):
    return PrimaryFeeAggregator.deploy(core, stable, FEE_AGG_CALLER_INCENTIVE, {"from": deployer})


@pytest.fixture(scope="module")
def staker(StableStaker, core, stable, fee_agg, reward_regulator, deployer):
    return StableStaker.deploy(
        core,
        stable,
        fee_agg,
        reward_regulator,
        "StableStaker",
        "SS",
        COOLDOWN_PERIOD,
        {"from": deployer},
    )


@pytest.fixture(scope="module")
def mock_stable_oracle(PriceOracleMock, deployer):
    return PriceOracleMock.deploy(10**18, {"from": deployer})


@pytest.fixture(scope="module")
def reward_regulator(StakerRewardRegulator, core, mock_stable_oracle, deployer):
    return StakerRewardRegulator.deploy(
        core,
        mock_stable_oracle,
        REG_MIN_PRICE,
        REG_MAX_PRICE,
        REG_MIN_STAKER_PCT,
        REG_MAX_STAKER_PCT,
        {"from": deployer},
    )


@pytest.fixture(scope="module")
def mock_bridge_relay(accounts, core, relay_key, deployer):
    relay = accounts.at("0x0000000000000000000000000000000000000042", force=True)
    core.setAddress(relay_key, relay, {"from": deployer})

    return relay
