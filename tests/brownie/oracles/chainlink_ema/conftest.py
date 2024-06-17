from brownie import chain
import pytest


@pytest.fixture(scope="module")
def ema_calc(observations, decimals):
    smoothing = 2 / (observations + 1)

    def func(new_observations, last):
        last *= 10**decimals
        if not isinstance(new_observations, list):
            new_observations = [new_observations]
        for value in new_observations:
            value *= 10**decimals
            last = int((value * smoothing) + (last * (1 - smoothing)))

        return last

    return func


@pytest.fixture(scope="module", params=[10, 20])
def observations(request):
    return request.param


@pytest.fixture(scope="module", params=[8, 10])
def decimals(request):
    return request.param


@pytest.fixture(scope="module")
def sleep_max_lookback(oracle, observations):
    """
    Sleeps to the edge of the "lookback" period, where the EMA is generated new
    instead of advancing from stored data. Use `offset` to sleep just before or after.
    """
    stored = oracle.storedObservationTimestamp()
    lookback_ends = stored + (observations * 100 * 2)

    def func(offset=0):
        chain.mine(timestamp=lookback_ends + offset)

    return func


@pytest.fixture(scope="module")
def chainlink(ChainlinkAggregatorMock, decimals, deployer):
    return ChainlinkAggregatorMock.deploy(decimals, 0, {"from": deployer})


@pytest.fixture(scope="module")
def oracle(ChainlinkEMA, chainlink, observations, deployer):
    chain.mine(timestamp=(chain.time() // 100 * 100) + 101)
    chainlink.add_round(3000, {"from": deployer})
    return ChainlinkEMA.deploy(chainlink, observations, 100, {"from": deployer})
