import pytest


@pytest.fixture(scope="module")
def uptime_cl(ChainlinkAggregatorMock, deployer):
    mock = ChainlinkAggregatorMock.deploy(0, 0, {"from": deployer})
    mock.set_updated_at(1, {"from": deployer})

    return mock


@pytest.fixture(scope="module")
def uptime_oracle(Layer2UptimeOracle, uptime_cl, deployer):
    return Layer2UptimeOracle.deploy(uptime_cl, {"from": deployer})
