import brownie
import pytest


@pytest.mark.parametrize("is_enabled", [True, False])
def test_set_is_enabled(converter, deployer, is_enabled):
    converter.setIsEnabled(is_enabled, {"from": deployer})
    assert converter.isEnabled() == is_enabled


def test_set_primary_chain_fee_agg(converter, alice, deployer):
    converter.setPrimaryChainFeeAggregator(alice, {"from": deployer})
    assert converter.primaryChainFeeAggregator() == alice


def test_set_swap_bonus_pct(converter, deployer):
    converter.setSwapBonusPctBps(5000, {"from": deployer})
    assert converter.swapBonusPctBps() == 5000


def test_set_min_relay_balance(converter, deployer):
    converter.setRelayMinBalance(88888, {"from": deployer})
    assert converter.relayMinBalance() == 88888


def test_set_max_relay_swap_debt_amount(converter, deployer):
    converter.setRelayMaxSwapDebtAmount(777, {"from": deployer})
    assert converter.relayMaxSwapDebtAmount() == 777


def test_set_token_approval(converter, collateral, alice, deployer):
    converter.setTokenApproval(collateral, alice, 31337, {"from": deployer})
    assert collateral.allowance(converter, alice) == 31337


def test_set_swap_bonus_pct_too_large(converter, deployer):
    with brownie.reverts("DFM: pct > MAX_PCT"):
        converter.setSwapBonusPctBps(10001, {"from": deployer})


def test_set_is_enabled_onlyowner(converter, alice):
    with brownie.reverts("DFM: Only owner"):
        converter.setIsEnabled(False, {"from": alice})


def test_set_primary_chain_fee_agg_onlyowner(converter, alice):
    with brownie.reverts("DFM: Only owner"):
        converter.setPrimaryChainFeeAggregator(alice, {"from": alice})


def test_set_swap_bonus_pct_onlyowner(converter, alice):
    with brownie.reverts("DFM: Only owner"):
        converter.setSwapBonusPctBps(5000, {"from": alice})


def test_set_min_relay_balance_onlyowner(converter, alice):
    with brownie.reverts("DFM: Only owner"):
        converter.setRelayMinBalance(88888, {"from": alice})


def test_set_max_relay_swap_debt_amount_onlyowner(converter, alice):
    with brownie.reverts("DFM: Only owner"):
        converter.setRelayMaxSwapDebtAmount(777, {"from": alice})


def test_set_token_approval_onlyowner(converter, collateral, alice):
    with brownie.reverts("DFM: Only owner"):
        converter.setTokenApproval(collateral, alice, 31337, {"from": alice})
