from brownie import chain


def test_sequencer_working(uptime_oracle, uptime_cl):
    assert uptime_cl.latestRoundData()[1] == 0
    assert uptime_oracle.getUptimeStatus() is True


def test_sequencer_down(uptime_oracle, uptime_cl, deployer):
    uptime_cl.set_price(1, {"from": deployer})

    assert uptime_cl.latestRoundData()[1] == 1
    assert uptime_oracle.getUptimeStatus() is False


def test_sequencer_up_in_grace_period(uptime_oracle, uptime_cl, deployer):
    timestamp = chain[-1].timestamp
    uptime_cl.set_price(0, {"from": deployer})
    uptime_cl.set_updated_at(timestamp, {"from": deployer})

    chain.mine(timestamp=timestamp + 1780)

    assert uptime_cl.latestRoundData()[1:3] == (0, timestamp)
    assert uptime_oracle.getUptimeStatus() is False


def test_sequencer_up_after_grace_period(uptime_oracle, uptime_cl, deployer):
    timestamp = chain[-1].timestamp
    uptime_cl.set_price(0, {"from": deployer})
    uptime_cl.set_updated_at(timestamp, {"from": deployer})

    chain.mine(timestamp=timestamp + 1801)

    assert uptime_cl.latestRoundData()[1:3] == (0, timestamp)
    assert uptime_oracle.getUptimeStatus() is True
