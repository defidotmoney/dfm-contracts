import pytest

from brownie import ZERO_ADDRESS


@pytest.fixture(scope="module")
def uptime_cl(ChainlinkAggregatorMock, deployer):
    mock = ChainlinkAggregatorMock.deploy(0, 0, {"from": deployer})
    mock.set_updated_at(1, {"from": deployer})

    return mock


@pytest.fixture(scope="module")
def uptime_oracle(Layer2UptimeOracle, uptime_cl, deployer):
    return Layer2UptimeOracle.deploy(uptime_cl, {"from": deployer})


@pytest.fixture(scope="module")
def uniswap(MockUniOracleReader, deployer):
    return MockUniOracleReader.deploy({"from": deployer})


@pytest.fixture(scope="module")
def curve(TricryptoMock, deployer):
    return TricryptoMock.deploy([ZERO_ADDRESS] * 3, {"from": deployer})


@pytest.fixture(scope="module")
def curve2(TricryptoMock, deployer):
    return TricryptoMock.deploy([ZERO_ADDRESS] * 3, {"from": deployer})


@pytest.fixture(scope="module")
def curve3(TricryptoMock, deployer):
    return TricryptoMock.deploy([ZERO_ADDRESS] * 3, {"from": deployer})


@pytest.fixture(scope="module")
def chained_oracle(AggregateChainedOracle, core, deployer):
    return AggregateChainedOracle.deploy(core, ZERO_ADDRESS, {"from": deployer})
