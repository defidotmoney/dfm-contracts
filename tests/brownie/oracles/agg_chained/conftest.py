import pytest

from brownie import ZERO_ADDRESS


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
