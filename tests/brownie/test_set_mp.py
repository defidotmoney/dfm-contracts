import brownie
from brownie import ZERO_ADDRESS


def test_initial_setup(controller, market, policy):
    assert controller.n_monetary_policies() == 1
    assert controller.monetary_policies(0) == policy
    assert controller.monetary_policies(1) == ZERO_ADDRESS

    assert controller.get_monetary_policy_for_market(market) == policy


def test_add_new_monetary_policy(controller, market, policy, alice, deployer):
    controller.add_new_monetary_policy(alice, {'from': deployer})

    assert controller.n_monetary_policies() == 2

    assert controller.monetary_policies(0) == policy
    assert controller.monetary_policies(1) == alice
    assert controller.monetary_policies(2) == ZERO_ADDRESS

    assert controller.get_monetary_policy_for_market(market) == policy


def test_change_existing_monetary_policy(controller, market, alice, deployer):
    controller.change_existing_monetary_policy(alice, 0, {'from': deployer})

    assert controller.n_monetary_policies() == 1
    assert controller.monetary_policies(0) == alice
    assert controller.monetary_policies(1) == ZERO_ADDRESS

    assert controller.get_monetary_policy_for_market(market) == alice



def test_change_existing_monetary_policy_invalid_mp_idx(controller, alice, deployer):
    with brownie.reverts():
        controller.change_existing_monetary_policy(alice, 1, {'from': deployer})


def test_change_market_monetary_policy(controller, market, policy, alice, deployer):
    controller.add_new_monetary_policy(alice, {'from': deployer})
    
    controller.change_market_monetary_policy(market, 1, {'from': deployer})
    assert controller.get_monetary_policy_for_market(market) == alice

    controller.change_market_monetary_policy(market, 0, {'from': deployer})
    assert controller.get_monetary_policy_for_market(market) == policy



def test_change_market_monetary_policy_invalid_mp_idx(controller, market, policy, alice, deployer):
    with brownie.reverts():
        controller.change_market_monetary_policy(market, 1, {'from': deployer})


def test_acl(controller, market, alice):
    with brownie.reverts():
        controller.add_new_monetary_policy(alice, {'from': alice})
    
    with brownie.reverts():
        controller.change_existing_monetary_policy(alice, 0, {'from': alice})

    
    with brownie.reverts():
        controller.change_market_monetary_policy(market, 0, {'from': alice})