from brownie import chain
import pytest


def test_initial_ema(oracle, decimals):
    assert oracle.price() == 3000 * 10**decimals
    assert oracle.price_w.call() == 3000 * 10**decimals


def test_calc_latest_new_round(oracle, chainlink, ema_calc, deployer):
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 50)
    chainlink.add_round(3250, {"from": deployer})
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 102)

    assert oracle.price() == ema_calc(3250, 3000)


def test_calc_latest_new_round_new_phase(oracle, chainlink, ema_calc, deployer):
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 50)
    chainlink.add_round(3250, True, {"from": deployer})
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 102)

    assert oracle.price() == ema_calc(3250, 3000)


def test_calc_latest_multiple_rounds_between_obs(oracle, chainlink, ema_calc, deployer):
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 50)
    chainlink.add_round(3250, {"from": deployer})
    chainlink.add_round(3600, {"from": deployer})
    chainlink.add_round(2700, {"from": deployer})
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 102)

    # because all 3 rounds happened between the 2 observation periods, only the last is used
    assert oracle.price() == ema_calc(2700, 3000)


def test_calc_latest_multiple_rounds_between_obs_with_write(oracle, chainlink, ema_calc, deployer):
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 50)
    chainlink.add_round(3250, {"from": deployer})
    chainlink.add_round(3600, {"from": deployer})

    # this shouldn't change anything
    oracle.price_w({"from": deployer})

    chainlink.add_round(2700, {"from": deployer})
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 102)

    assert oracle.price() == ema_calc(2700, 3000)


def test_calc_latest_multiple_obs_latest_round(oracle, chainlink, ema_calc, deployer):
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 50)
    chainlink.add_round(3600, {"from": deployer})
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 302)

    assert oracle.price() == ema_calc([3600, 3600, 3600], 3000)


def test_calc_latest_multiple_obs_latest_round_with_write(oracle, chainlink, ema_calc, deployer):
    chain.mine(timestamp=oracle.storedObservationTimestamp() + 50)
    chainlink.add_round(3600, {"from": deployer})
    for _ in range(3):
        chain.sleep(100)
        oracle.price_w({"from": deployer})

    assert oracle.price() == ema_calc([3600, 3600, 3600], 3000)


def test_max_lookback(
    oracle, chainlink, ema_calc, observations, decimals, sleep_max_lookback, deployer
):
    stored = oracle.storedObservationTimestamp()
    chain.mine(timestamp=stored + 50)
    chainlink.add_round(4100, {"from": deployer})
    sleep_max_lookback(-50)
    # chain.mine(timestamp=stored + (100 * observations * 2) - 50)

    # last stored observation was LOOKBACK - 1 periods ago, the oracle is still advancing the EMA
    assert oracle.price() == ema_calc([4100] * (observations * 2 - 1), 3000)

    # last stored observation is now LOOKBACK periods ago, oracle calculates a new EMA
    sleep_max_lookback()
    # chain.mine(timedelta=100)
    assert oracle.price() == 4100 * 10**decimals


@pytest.mark.parametrize("new_phase", [True, False])
def test_calc_latest_complex(oracle, chainlink, ema_calc, deployer, new_phase):
    stored = oracle.storedObservationTimestamp()
    chain.mine(timestamp=stored + 150)
    chainlink.add_round(3200, {"from": deployer})
    chain.mine(timestamp=stored + 450)
    chainlink.add_round(3550, new_phase, {"from": deployer})
    chain.mine(timestamp=stored + 650)
    chainlink.add_round(3750, {"from": deployer})
    chainlink.add_round(3410, new_phase, {"from": deployer})
    chain.mine(timestamp=stored + 750)
    chainlink.add_round(2900, {"from": deployer})
    chain.mine(timestamp=stored + 950)

    observations = [3000, 3200, 3200, 3200, 3550, 3550, 3410, 2900, 2900]
    assert oracle.price() == ema_calc(observations, 3000)
