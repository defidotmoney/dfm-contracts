// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import { CoreOwnable } from "./CoreOwnable.sol";

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
abstract contract DelegatedOps is CoreOwnable {
    event SetDelegateApproval(address indexed caller, address indexed delegate, bool isApproved);
    event SetDelegationEnabled(address caller, bool isEnabled);

    mapping(address owner => mapping(address caller => bool isApproved)) public isApprovedDelegate;

    bool public isDelegationEnabled;

    constructor(address _core) CoreOwnable(_core) {
        isDelegationEnabled = true;
    }

    modifier callerOrDelegated(address _account) {
        if (msg.sender != _account) {
            require(isDelegationEnabled, "DFM: Delegation disabled");
            require(isApprovedDelegate[_account][msg.sender], "DFM: Delegate not approved");
        }
        _;
    }

    /**
        @notice Enable or disable a delegate to perform actions on behalf of the caller
        @param _delegate Address of the delegate to set approval for
        @param _isApproved Is delegate approved?
     */
    function setDelegateApproval(address _delegate, bool _isApproved) external {
        isApprovedDelegate[msg.sender][_delegate] = _isApproved;
        emit SetDelegateApproval(msg.sender, _delegate, _isApproved);
    }

    /**
        @notice Enable or disable all delegated operations within this contract
        @dev Delegated operations are enabled by default upon deployment.
             Only the owner can enable. The owner or the guardian can disable.
        @param _isEnabled Are delegated operations approved?
     */
    function setDelegationEnabled(bool _isEnabled) external ownerOrGuardianToggle(_isEnabled) {
        isDelegationEnabled = _isEnabled;
        emit SetDelegationEnabled(msg.sender, _isEnabled);
    }
}
