# @version 0.3.10

response: public(int256)
is_reverting: public(bool)
hook_type: public(uint256)
active_hooks: public(bool[4])


event HookFired:
    pass


@external
def set_configuration(hook_type: uint256, active_hooks: bool[4]):
    self.hook_type = hook_type
    self.active_hooks = active_hooks


@view
@external
def get_configuration() -> (uint256, bool[4]):
    return self.hook_type, self.active_hooks


@external
def set_response(response: int256):
    self.response = response

@external
def set_is_reverting(is_reverting: bool):
    self.is_reverting = is_reverting

@view
@internal
def _get_response() -> int256:
    if self.is_reverting:
        raise "Hook is reverting"

    return self.response

@external
def on_create_loan(account: address, controller: address, coll_amount: uint256, debt_amount: uint256) -> int256:
    log HookFired()
    return self._get_response()

@external
def on_adjust_loan(account: address, controller: address, coll_change: int256, debt_changet: int256) -> int256:
    log HookFired()
    return self._get_response()

@external
def on_close_loan(account: address, controller: address, account_debt: uint256) -> int256:
    log HookFired()
    return self._get_response()

@external
def on_liquidation(sender: address, controller: address, target: address, debt_liquidated: uint256) -> int256:
    log HookFired()
    return self._get_response()

@view
@external
def on_create_loan_view(account: address, controller: address, coll_amount: uint256, debt_amount: uint256) -> int256:
    return self._get_response()

@view
@external
def on_adjust_loan_view(account: address, controller: address, coll_change: int256, debt_changet: int256) -> int256:
    return self._get_response()

@view
@external
def on_close_loan_view(account: address, controller: address, account_debt: uint256) -> int256:
    return self._get_response()

@view
@external
def on_liquidation_view(sender: address, controller: address, target: address, debt_liquidated: uint256) -> int256:
    return self._get_response()