# @version 0.3.10

from vyper.interfaces import ERC20

COLLATERAL: immutable(ERC20)
AMM: immutable(address)

event OnAddHook: pass
event OnRemoveHook: pass
event BeforeCollOut: pass
event AfterCollIn: pass


@external
def __init__(collateral: ERC20, amm: address):
    COLLATERAL = collateral
    AMM = amm

@external
def on_add_hook(market: address, amm: address) -> bool:
    assert msg.sender == AMM
    amount: uint256 = COLLATERAL.balanceOf(AMM)
    COLLATERAL.transferFrom(AMM, self, amount)
    log OnAddHook()
    return True

@external
def on_remove_hook() -> bool:
    assert msg.sender == AMM
    amount: uint256 = COLLATERAL.balanceOf(self)
    COLLATERAL.transfer(msg.sender, amount)
    log OnRemoveHook()
    return True

@external
def before_collateral_out(amount: uint256) -> bool:
    COLLATERAL.transfer(AMM, amount)
    log BeforeCollOut()
    return True

@external
def after_collateral_in(amount: uint256) -> bool:
    COLLATERAL.transferFrom(AMM, self, amount)
    log AfterCollIn()
    return True