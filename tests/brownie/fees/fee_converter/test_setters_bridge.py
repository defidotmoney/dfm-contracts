import brownie


def test_set_bridge_bonus_pct(converter_bridge, deployer):
    converter_bridge.setBridgeBonusPctBps(1234, {"from": deployer})
    assert converter_bridge.bridgeBonusPctBps() == 1234

    converter_bridge.setBridgeBonusPctBps(0, {"from": deployer})
    assert converter_bridge.bridgeBonusPctBps() == 0

    with brownie.reverts("DFM: pct > MAX_PCT"):
        converter_bridge.setBridgeBonusPctBps(10001, {"from": deployer})

    converter_bridge.setBridgeBonusPctBps(10000, {"from": deployer})
    assert converter_bridge.bridgeBonusPctBps() == 10000


def test_set_max_bridge_bonus_amount(converter_bridge, deployer):
    converter_bridge.setBridgeMaxBonusAmount(987654321, {"from": deployer})
    assert converter_bridge.bridgeMaxBonusAmount() == 987654321

    converter_bridge.setBridgeMaxBonusAmount(0, {"from": deployer})
    assert converter_bridge.bridgeMaxBonusAmount() == 0


def test_set_bridge_bonus_pct_only_owner(converter_bridge, alice):
    with brownie.reverts("DFM: Only owner"):
        converter_bridge.setBridgeBonusPctBps(1234, {"from": alice})


def test_set_max_bridge_bonus_amount_only_owner(converter_bridge, alice):
    with brownie.reverts("DFM: Only owner"):
        converter_bridge.setRelayMaxSwapDebtAmount(987654321, {"from": alice})
