import pytest
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(stable, controller, staker, alice, fee_agg):
    for acct in [alice, fee_agg]:
        stable.mint(acct, 10**30, {"from": controller})
        stable.approve(staker, 2**256 - 1, {"from": acct})

    chain.mine(timedelta=604800)


def test_initial_assumptions(staker):
    assert staker.lastUpdate() // 604800 < chain[-1].timestamp // 604800


@pytest.mark.parametrize("amount", [10**18, 148 * 10**13, 88888 * 10**22])
def test_daily_stream_rps_duration(staker, stable, alice, fee_agg, amount):
    staker.deposit(10**18, alice, {"from": alice})

    amount = amount // (604800 * 2) * (604800 * 2)

    stable.transfer(staker, amount, {"from": fee_agg})
    tx = staker.notifyNewFees(amount, {"from": fee_agg})

    # new stream should last 2 days
    assert staker.periodFinish() == tx.timestamp + 86400 * 2

    # per-second amount should be 1/7th split over 2 days
    assert staker.rewardsPerSecond() == amount // 7 // 86400 // 2


@pytest.mark.parametrize("amount", [148 * 10**13, 88888 * 10**22])
def test_daily_stream_updates_next_day(staker, stable, alice, fee_agg, amount):
    staker.deposit(10**18, alice, {"from": alice})

    amount = amount // (604800 * 2) * (604800 * 2)

    stable.transfer(staker, amount, {"from": fee_agg})
    tx = staker.notifyNewFees(amount, {"from": fee_agg})

    next_day = (tx.timestamp // 86400 + 1) * 86400
    period_start = tx.timestamp
    period_finish = staker.periodFinish()
    rps = staker.rewardsPerSecond()

    # mint within same day does not affect
    chain.mine(timestamp=next_day - 10)
    staker.mint(0, alice, {"from": alice})
    assert staker.periodFinish() == period_finish
    assert staker.rewardsPerSecond() == rps

    # mint in new day restarts the stream
    chain.mine(timedelta=11)
    tx = staker.mint(0, alice, {"from": alice})
    assert staker.periodFinish() == tx.timestamp + 86400 * 2
    remaining_rps = ((period_finish - tx.timestamp) * rps) // 86400 // 2
    assert staker.rewardsPerSecond() == rps + remaining_rps


@pytest.mark.parametrize("amount", [148 * 10**15, 88888 * 10**22])
@pytest.mark.parametrize("days", [2, 6, 12])
def test_daily_stream_update_several_days(staker, stable, alice, fee_agg, amount, days):
    staker.deposit(10**18, alice, {"from": alice})

    amount = amount // (604800 * 2) * (604800 * 2)

    stable.transfer(staker, amount, {"from": fee_agg})
    staker.notifyNewFees(amount, {"from": fee_agg})
    rps = staker.rewardsPerSecond()

    # with > 2 days past, the old stream has finished
    # rps is increased to account for the missed days
    chain.mine(timedelta=86400 * days + 1)
    tx = staker.mint(0, alice, {"from": alice})
    assert staker.periodFinish() == tx.timestamp + 86400 * 2
    assert staker.rewardsPerSecond() == rps * min(days, 6)


@pytest.mark.parametrize("amount", [10**18, 148 * 10**15])
def test_single_period(staker, stable, alice, fee_agg, amount):
    staker.deposit(10**18, alice, {"from": alice})

    amount = amount // (604800 * 2) * (604800 * 2)

    stable.transfer(staker, amount, {"from": fee_agg})
    tx = staker.notifyNewFees(amount, {"from": fee_agg})

    period_start = tx.timestamp
    period_finish = staker.periodFinish()
    rps = amount // 7 // 86400 // 2

    while chain[-1].timestamp < period_finish:
        total_assets = staker.totalAssets()
        assert total_assets == 10**18 + rps * (chain[-1].timestamp - period_start)
        chain.mine(timedelta=25000)

    total_assets = staker.totalAssets()
    assert total_assets == 10**18 + amount // 7

    for i in range(1, 11):
        shares = 10**18 // i
        assets = total_assets // i
        assert 0 <= assets - staker.convertToAssets(shares) <= 1
        assert 0 <= shares - staker.convertToShares(assets) <= 1


@pytest.mark.parametrize("amount", [10**18, 148 * 10**15])
def test_multiple_periods(staker, stable, alice, fee_agg, amount):
    staker.deposit(10**18, alice, {"from": alice})

    amount = amount // (604800 * 2) * (604800 * 2)
    expected = amount // 7

    stable.transfer(staker, amount, {"from": fee_agg})
    tx = staker.notifyNewFees(amount, {"from": fee_agg})

    total = 10**18
    rps = staker.rewardsPerSecond()
    for _ in range(6):
        chain.mine(timestamp=chain[-1].timestamp + 86400)
        total += expected // 2
        assert abs(staker.totalAssets() - total) < amount // 604800

        staker.mint(0, alice, {"from": alice})
        assert staker.rewardsPerSecond() > rps
        assert staker.periodFinish() == chain[-1].timestamp + 86400 * 2

        rps = staker.rewardsPerSecond()
        expected = (expected // 2) + (amount // 7)

    chain.mine(timedelta=86400 * 2)
    staker.mint(0, alice, {"from": alice})
    assert staker.rewardsPerSecond() == rps
    assert staker.periodFinish() < chain[-1].timestamp

    assert 0 <= (10**18 + amount) - staker.totalAssets() < amount // 604800


def test_daily_updates_do_not_start_new_week(staker, stable, alice, fee_agg):
    staker.deposit(10**18, alice, {"from": alice})
    amount = 10**18 // (604800 * 2) * (604800 * 2)

    stable.transfer(staker, amount, {"from": fee_agg})
    staker.notifyNewFees(amount, {"from": fee_agg})

    chain.mine(timedelta=86400 * 7 + 1)
    tx = staker.mint(0, alice, {"from": alice})

    period_finish = staker.periodFinish()
    rps = staker.rewardsPerSecond()
    last_day = staker.lastDistributionDay()

    chain.mine(timedelta=86400 * 2 + 1)
    staker.mint(0, alice, {"from": alice})

    assert staker.periodFinish() == period_finish
    assert staker.rewardsPerSecond() == rps
    assert staker.lastDistributionDay() == last_day
