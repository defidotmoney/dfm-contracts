# @version 0.3.10

response: public(int256)
is_reverting: public(bool)

event HookFired:
    pass

@external
def set_response(response: int256):
    self.response = response

@external
def set_is_reverting(is_reverting: bool):
    self.is_reverting = is_reverting

@internal
def _get_response() -> int256:
    if self.is_reverting:
        raise "Hook is reverting"

    log HookFired()
    return self.response

@external
def on_create_loan(account: address, controller: address, coll_amount: uint256, debt_amount: uint256) -> int256:
    return self._get_response()

@external
def on_adjust_loan(account: address, controller: address, coll_change: int256, debt_changet: int256) -> int256:
    return self._get_response()

@external
def on_close_loan(account: address, controller: address, account_debt: uint256) -> int256:
    return self._get_response()

@external
def on_liquidation(sender: address, controller: address, target: address, debt_liquidated: uint256) -> int256:
    return self._get_response()