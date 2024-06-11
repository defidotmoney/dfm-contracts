import pytest

import brownie


@pytest.fixture(scope="module", autouse=True)
def setup(stable, alice, deployer):
    stable.setMinter(alice, True, {"from": deployer})


def test_initial_state(stable):
    assert stable.isBridgeEnabled()
    assert stable.isFlashMintEnabled()
    assert stable.maxFlashLoan(stable) == 2**127


def test_disable_bridge_guardian(stable, guardian, alice):
    stable.setBridgeEnabled(False, {"from": guardian})

    assert not stable.isBridgeEnabled()

    with brownie.reverts("DFM:T Bridging disabled"):
        stable.sendSimple(0, alice, 10**18, {"from": alice})


def test_disable_mint_owner(stable, alice, deployer):
    stable.setBridgeEnabled(False, {"from": deployer})

    assert not stable.isBridgeEnabled()


def test_enable_mint_owner(stable, guardian, alice, deployer):
    stable.setBridgeEnabled(False, {"from": guardian})
    stable.setBridgeEnabled(True, {"from": deployer})

    assert stable.isBridgeEnabled()

    with brownie.reverts("ERC20: burn amount exceeds balance"):
        stable.sendSimple(0, alice, 10**18, {"from": alice})


def test_enable_mint_reverts_guardian(stable, guardian):
    stable.setBridgeEnabled(False, {"from": guardian})

    with brownie.reverts("DFM:T Guardian can only disable"):
        stable.setBridgeEnabled(True, {"from": guardian})


def test_set_mint_reverts_general(stable, alice):
    for enabled in [True, False]:
        with brownie.reverts("DFM:T Not owner or guardian"):
            stable.setBridgeEnabled(enabled, {"from": alice})


def test_disable_flashmint_guardian(stable, guardian, alice):
    stable.setFlashMintEnabled(False, {"from": guardian})

    assert not stable.isFlashMintEnabled()
    assert stable.maxFlashLoan(stable) == 0

    # minting should still be possible
    stable.mint(alice, 10**18, {"from": alice})


def test_disable_flashmint_owner(stable, alice, deployer):
    stable.setFlashMintEnabled(False, {"from": deployer})

    assert not stable.isFlashMintEnabled()
    assert stable.maxFlashLoan(stable) == 0

    stable.mint(alice, 10**18, {"from": alice})


def test_enable_flashmint_owner(stable, guardian, alice, deployer):
    stable.setFlashMintEnabled(False, {"from": guardian})
    stable.setFlashMintEnabled(True, {"from": deployer})

    assert stable.isFlashMintEnabled()
    assert stable.maxFlashLoan(stable) == 2**127


def test_enable_flashmint_reverts_guardian(stable, guardian):
    stable.setFlashMintEnabled(False, {"from": guardian})

    with brownie.reverts("DFM:T Guardian can only disable"):
        stable.setFlashMintEnabled(True, {"from": guardian})


def test_set_flashmint_reverts_general(stable, alice):
    for enabled in [True, False]:
        with brownie.reverts("DFM:T Not owner or guardian"):
            stable.setFlashMintEnabled(enabled, {"from": alice})
