import pytest
from brownie import chain


@pytest.fixture(scope="module")
def share_price_setup(stable, controller, staker, alice, bob, fee_agg):
    # MODULES USING THIS FIXTURE MUST INHERIT VIA AN AUTOUSE SETUP FIXTURE
    for acct in [alice, bob, fee_agg]:
        stable.mint(acct, 10**24, {"from": controller})
        stable.approve(staker, 2**256 - 1, {"from": acct})

    staker.deposit(10**18, fee_agg, {"from": fee_agg})


@pytest.fixture(scope="function", params=[4 * 10**17, 10**18, 88 * 10**19])
def reward_amount(share_price_setup, stable, staker, fee_agg, request):
    amount = request.param // (604800 * 2) * (604800 * 2)
    stable.transfer(staker, amount, {"from": fee_agg})
    staker.notifyNewFees(amount, {"from": fee_agg})
    chain.mine(timedelta=86400 * 7 + 1)
    staker.mint(0, fee_agg, {"from": fee_agg})
    chain.mine(timedelta=86400 * 2 + 1)
    return amount


@pytest.fixture(scope="function")
def initial_total_assets(reward_amount):
    return 10**18 + reward_amount


@pytest.fixture(scope="function")
def to_shares(reward_amount):
    def _to_shares(assets):
        return assets * 10**18 // (10**18 + reward_amount)

    return _to_shares


@pytest.fixture(scope="function")
def to_assets(reward_amount):
    def _to_assets(shares):
        return shares * (10**18 + reward_amount) // 10**18

    return _to_assets
