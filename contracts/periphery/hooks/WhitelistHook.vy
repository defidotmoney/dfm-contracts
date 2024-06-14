#pragma version 0.3.10
"""
@title DFM Whitelist Hook
@dev Restricts creation of new loans to whitelisted addresses
@license MIT
"""

is_whitelisted: public(HashMap[address, bool])

owner: public(address)


@external
def __init__(owner: address):
    self.owner = owner


@view
@external
def get_configuration() -> (uint256, bool[4]):
    return 0, [True, False, False, False]


@view
@external
def on_create_loan_view(account: address, market: address, coll_amount: uint256, debt_amount: uint256) -> int256:
    return self._assert_is_whitelisted(account)


@external
def on_create_loan(account: address, market: address, coll_amount: uint256, debt_amount: uint256) -> int256:
    return self._assert_is_whitelisted(account)


@external
def set_owner(owner: address):
    assert msg.sender == self.owner, "DFM: only owner"
    self.owner = owner


@external
def set_whitelisted(accounts: DynArray[address, max_value(uint16)], is_whitelisted: bool):
    assert msg.sender == self.owner, "DFM: only owner"
    for account in accounts:
        self.is_whitelisted[account] = is_whitelisted


@view
@internal
def _assert_is_whitelisted(account: address) -> int256:
    assert self.is_whitelisted[account], "DFM: not whitelisted"
    return 0