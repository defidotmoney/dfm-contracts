# @version 0.3.10

from vyper.interfaces import ERC20

CONTROLLER: immutable(address)
COLLATERAL: immutable(ERC20)
AMM: immutable(address)

event OnAddHook: pass
event OnRemoveHook: pass
event BeforeCollOut: pass
event AfterCollIn: pass


is_transfer_enabled: public(bool)
is_reverting: public(bool)



@external
def __init__(controller: address, collateral: ERC20, amm: address):
    CONTROLLER = controller
    COLLATERAL = collateral
    AMM = amm
    self.is_transfer_enabled = True


@internal
def _assert_not_reverting():
    assert not self.is_reverting, "AMM Hook is reverting"

@external
def set_is_reverting(is_reverting: bool):
    self.is_reverting = is_reverting


@external
def set_is_transfer_enabled(is_transfer_enabled: bool):
    # disable transfers to test hook validation on add/remove
    self.is_transfer_enabled = is_transfer_enabled


@external
def on_add_hook(market: address, amm: address):
    assert msg.sender == AMM
    self._assert_not_reverting()
    if self.is_transfer_enabled:
        amount: uint256 = COLLATERAL.balanceOf(AMM)
        COLLATERAL.transferFrom(AMM, self, amount, default_return_value=True)
    log OnAddHook()


@external
def on_remove_hook():
    assert msg.sender == AMM
    self._assert_not_reverting()
    if self.is_transfer_enabled:
        amount: uint256 = COLLATERAL.balanceOf(self)
        COLLATERAL.transfer(msg.sender, amount, default_return_value=True)
    log OnRemoveHook()


@external
def before_collateral_out(amount: uint256):
    assert msg.sender in [CONTROLLER, AMM]
    self._assert_not_reverting()
    COLLATERAL.transfer(AMM, amount, default_return_value=True)
    log BeforeCollOut()


@external
def after_collateral_in(amount: uint256):
    assert msg.sender in [CONTROLLER, AMM]
    self._assert_not_reverting()
    COLLATERAL.transferFrom(AMM, self, amount, default_return_value=True)
    log AfterCollIn()


@view
@external
def collateral_balance() -> uint256:
    return COLLATERAL.balanceOf(self)
