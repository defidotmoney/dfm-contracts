import pytest

import brownie
from brownie import ZERO_ADDRESS


@pytest.mark.parametrize("i", range(4))
@pytest.mark.parametrize("is_global", [True, False])
def test_add_remove_max_hooks_views(market, hooks, many_hooks, controller, deployer, is_global, i):
    market = ZERO_ADDRESS if is_global else market

    hooks.set_configuration(1, [True, False, False, False], {"from": deployer})

    for contract in many_hooks:
        controller.add_market_hook(market, contract, {"from": deployer})

    hookdata = controller.get_market_hooks(market)
    assert len(hookdata) == 4
    for contract in many_hooks:
        data = next(x for x in hookdata if x[0] == contract)
        assert contract.get_configuration() == data[1:]

    with brownie.reverts("DFM:C Maximum hook count reached"):
        controller.add_market_hook(market, hooks, {"from": deployer})

    controller.remove_market_hook(market, many_hooks[i], {"from": deployer})

    hookdata = controller.get_market_hooks(market)
    assert len(hookdata) == 3
    for contract in many_hooks:
        if contract == many_hooks[i]:
            assert contract not in [x[0] for x in hookdata]
        else:
            data = next(x for x in hookdata if x[0] == contract)
            assert contract.get_configuration() == data[1:]

    controller.add_market_hook(market, hooks, {"from": deployer})

    with brownie.reverts("DFM:C Maximum hook count reached"):
        controller.add_market_hook(market, many_hooks[1], {"from": deployer})


def test_add_invalid_market(hooks, controller, alice, deployer):
    with brownie.reverts("DFM:C Invalid market"):
        controller.add_market_hook(alice, hooks, {"from": deployer})


def test_remove_invalid_market(hooks, controller, alice, deployer):
    with brownie.reverts("DFM:C Invalid market"):
        controller.remove_market_hook(alice, hooks, {"from": deployer})


def test_reverts_with_no_active(market, hooks, controller, deployer):
    hooks.set_configuration(0, [False, False, False, False], {"from": deployer})
    with brownie.reverts("DFM:C No active hook points"):
        controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})


def test_cannot_add_twice(market, controller, hooks, deployer):
    hooks.set_configuration(0, [True, False, False, False], {"from": deployer})

    controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})
    with brownie.reverts("DFM:C Hook already added"):
        controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})

    # ...but we can re-add it as a market specific hook
    controller.add_market_hook(market, hooks, {"from": deployer})

    # but not twice!
    with brownie.reverts("DFM:C Hook already added"):
        controller.add_market_hook(market, hooks, {"from": deployer})


def test_reverts_with_invalid_type(market, hooks, controller, deployer):
    hooks.set_configuration(3, [True, False, False, False], {"from": deployer})
    with brownie.reverts("DFM:C Invalid hook type"):
        controller.add_market_hook(ZERO_ADDRESS, hooks, {"from": deployer})


def test_cannot_remove_unknown(market, hooks, controller, deployer):
    with brownie.reverts("DFM:C Unknown hook"):
        controller.remove_market_hook(market, hooks, {"from": deployer})
