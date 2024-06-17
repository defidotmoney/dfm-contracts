from brownie import chain
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup(chainlink, sleep_max_lookback, deployer):
    # stored price is 3000, so we add a round at 4000 to make sure the stored value is unused
    chainlink.add_round(4000, {"from": deployer})
    sleep_max_lookback()


def test_calc_new_simple(oracle, chainlink, ema_calc, deployer):
    chainlink.batch_add_rounds([[3200, 50, False]], {"from": deployer})

    assert oracle.price() == ema_calc(3200, 4000)


def test_multiple_rounds(oracle, chainlink, ema_calc, deployer):
    chainlink.batch_add_rounds(
        [[3500, 250, False], [2800, 150, False], [3200, 50, False]], {"from": deployer}
    )

    assert oracle.price() == ema_calc([3500, 2800, 3200], 4000)


def test_multiple_rounds_same_answer(oracle, chainlink, ema_calc, deployer):
    chainlink.batch_add_rounds([[3600, 450, False], [3200, 50, False]], {"from": deployer})

    assert oracle.price() == ema_calc([3600, 3600, 3600, 3600, 3200], 4000)


def test_new_phase(oracle, chainlink, ema_calc, deployer):
    chainlink.batch_add_rounds(
        [[3500, 650, False], [2800, 550, True], [3200, 50, False]], {"from": deployer}
    )

    assert oracle.price() == ema_calc([3200], 2800)


def test_multiple_answers_same_round(oracle, chainlink, ema_calc, deployer):
    chainlink.batch_add_rounds(
        [[2800, 280, False], [3500, 250, False], [3400, 240, False], [3700, 50, False]],
        {"from": deployer},
    )

    assert oracle.price() == ema_calc([3400, 3400, 3700], 4000)


def test_new_phase_too_recently(oracle, chainlink, deployer):
    chain.sleep(5)

    # adding this round without a phase update should not affect the oracle price
    # because it's more recent than the latest observation time
    chainlink.add_round(6666, False, {"from": deployer})
    assert oracle.price() == 4000 * 10**18

    # now we add with a phase update, because we're outside the lookback period
    # the oracle will return the same price
    chainlink.add_round(69420, True, {"from": deployer})
    assert oracle.price() == 69420 * 10**18
