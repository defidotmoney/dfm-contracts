import brownie


def test_add_receivers(fee_agg, alice):
    with brownie.reverts("DFM: Only owner"):
        fee_agg.addPriorityReceivers([], {"from": alice})


def test_remove_receiver(fee_agg, alice):
    with brownie.reverts("DFM: Only owner"):
        fee_agg.removePriorityReceiver(0, {"from": alice})


def test_set_fallback(fee_agg, alice):
    with brownie.reverts("DFM: Only owner"):
        fee_agg.setFallbackReceiver(alice, {"from": alice})


def test_set_caller_incentive(fee_agg, alice):
    with brownie.reverts("DFM: Only owner"):
        fee_agg.setCallerIncentive(0, {"from": alice})
