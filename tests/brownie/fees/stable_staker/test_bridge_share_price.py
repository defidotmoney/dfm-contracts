import brownie

import pytest
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup_mod(share_price_setup, stable, staker, alice, fee_agg, deployer):
    staker.setPeer(42, staker.address, {"from": deployer})

    staker.deposit(10**18, alice, {"from": alice})

    stable.transfer(staker, 10**18, {"from": fee_agg})
    staker.notifyNewFees(10**18, {"from": fee_agg})

    chain.mine(timedelta=86400 * 7 + 1)
    staker.mint(0, fee_agg, {"from": fee_agg})
    chain.mine(timedelta=86400 * 2 + 1)


def test_initial_assumptions(staker):
    assert staker.totalSupply() == 2 * 10**18
    assert staker.totalMintedSupply() == 2 * 10**18

    assert 0 < (3 * 10**18) - staker.totalAssets() < 604800
    assert staker.convertToAssets(10**18) > 10**18


def test_bridge_out(staker, alice):
    assets = staker.convertToAssets(10**18)

    staker.sendSimple(42, alice, 10**17, {"from": alice, "value": 10**10})

    assert staker.totalSupply() == 2 * 10**18 - 10**17
    assert staker.totalMintedSupply() == 2 * 10**18
    assert staker.convertToAssets(10**18) == assets


def test_bridge_in(staker, mock_endpoint, alice, bob, deployer):
    assets = staker.convertToAssets(10**18)

    staker.sendSimple(42, alice, 3 * 10**17, {"from": alice, "value": 10**10})
    mock_endpoint.mockMintTokens(staker, bob, 42, 10**17, {"from": deployer})

    assert staker.totalSupply() == 2 * 10**18 - 2 * 10**17
    assert staker.totalMintedSupply() == 2 * 10**18
    assert staker.convertToAssets(10**18) == assets


def test_oversupply(staker, mock_endpoint, deployer):
    with brownie.reverts("DFM: Oversupply"):
        mock_endpoint.mockMintTokens(staker, deployer, 42, 10**17, {"from": deployer})
