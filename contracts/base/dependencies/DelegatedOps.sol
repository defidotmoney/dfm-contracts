// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/**
    @title Delegated Operations
    @author Prisma Finance (with edits by defidotmoney)
    @notice Allows delegation to specific contract functionality. Useful for creating
            wrapper contracts to bundle multiple interactions into a single call.

            Functions that supports delegation should include an `account` input allowing
            the delegated caller to indicate who they are calling on behalf of. In executing
            the call, all internal state updates should be applied for `account` and all
            value transfers should occur to or from the caller.
 */
abstract contract DelegatedOps {
    event SetDelegateApproval(address indexed caller, address indexed delegate, bool isApproved);

    mapping(address owner => mapping(address caller => bool isApproved)) public isApprovedDelegate;

    modifier callerOrDelegated(address _account) {
        require(msg.sender == _account || isApprovedDelegate[_account][msg.sender], "DFM: Delegate not approved");
        _;
    }

    function setDelegateApproval(address _delegate, bool _isApproved) external {
        isApprovedDelegate[msg.sender][_delegate] = _isApproved;
        emit SetDelegateApproval(msg.sender, _delegate, _isApproved);
    }
}
