import pytest

import brownie


@pytest.fixture(scope="module")
def wl_hook(WhitelistHook, deployer):
    return WhitelistHook.deploy(deployer, {"from": deployer})


@pytest.fixture(scope="module")
def wl_accounts(accounts):
    return accounts[-5:]


@pytest.fixture(scope="module")
def non_wl_accounts(accounts):
    return accounts[:-5]


@pytest.fixture(scope="module", autouse=True)
def setup(wl_hook, market, collateral, controller, alice, deployer):
    collateral._mint_for_testing(alice, 100 * 10**18)
    collateral.approve(controller, 2**256 - 1, {"from": alice})

    controller.add_market_hook(market, wl_hook, {"from": deployer})


def test_hook_config(wl_hook, controller, market):
    data = controller.get_market_hooks(market)
    assert data == [(wl_hook, 0, [True, False, False, False])]


def test_no_initial_whitelisting(wl_hook, wl_accounts, non_wl_accounts):
    for acct in wl_accounts + non_wl_accounts:
        assert not wl_hook.is_whitelisted(acct)


def test_add_to_whitelist(wl_hook, wl_accounts, deployer):
    wl_hook.set_whitelisted(wl_accounts, True, {"from": deployer})

    for acct in wl_accounts:
        assert wl_hook.is_whitelisted(acct)


def test_remove_from_whitelist(wl_hook, wl_accounts, deployer):
    wl_hook.set_whitelisted(wl_accounts, True, {"from": deployer})
    wl_hook.set_whitelisted(wl_accounts[:2], False, {"from": deployer})

    assert not wl_hook.is_whitelisted(wl_accounts[0])
    assert not wl_hook.is_whitelisted(wl_accounts[1])
    assert wl_hook.is_whitelisted(wl_accounts[2])


def test_noop(wl_hook, wl_accounts, non_wl_accounts, deployer):
    wl_hook.set_whitelisted(wl_accounts, True, {"from": deployer})
    wl_hook.set_whitelisted(wl_accounts, True, {"from": deployer})

    wl_hook.set_whitelisted(non_wl_accounts, False, {"from": deployer})

    for acct in wl_accounts:
        assert wl_hook.is_whitelisted(acct)

    for acct in non_wl_accounts:
        assert not wl_hook.is_whitelisted(acct)


def test_set_whitelist_acl(wl_hook, alice):
    with brownie.reverts("DFM: only owner"):
        wl_hook.set_whitelisted([alice], True, {"from": alice})


def test_set_owner_acl(wl_hook, alice):
    with brownie.reverts("DFM: only owner"):
        wl_hook.set_owner(alice, {"from": alice})


def test_create_loan_whitelisted(wl_hook, controller, market, alice, deployer):
    wl_hook.set_whitelisted([alice], True, {"from": deployer})

    controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})


def test_create_loan_not_whitelisted(controller, market, alice):
    with brownie.reverts("DFM: not whitelisted"):
        controller.create_loan(alice, market, 50 * 10**18, 1000 * 10**18, 5, {"from": alice})
