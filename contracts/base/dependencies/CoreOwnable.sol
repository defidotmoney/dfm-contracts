// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import { IProtocolCore } from "../../interfaces/IProtocolCore.sol";

/**
    @title Core Ownable
    @author Prisma Finance (with edits by defidotmoney)
    @notice Contracts inheriting `CoreOwnable` have the same owner as `ProtocolCore`.
            The ownership cannot be independently modified or renounced.
 */
abstract contract CoreOwnable {
    IProtocolCore public immutable CORE_OWNER;

    constructor(address _core) {
        CORE_OWNER = IProtocolCore(_core);
    }

    modifier onlyOwner() {
        require(msg.sender == address(CORE_OWNER.owner()), "DFM: Only owner");
        _;
    }

    modifier onlyBridgeRelay() {
        require(msg.sender == bridgeRelay(), "DFM: Only bridge relay");
        _;
    }

    /**
        @dev Access control modifier for toggle actions where the only the protocol
             owner is allowed to enabled, but both the owner and guardian can disable.
     */
    modifier ownerOrGuardianToggle(bool isEnabled) {
        if (msg.sender != owner()) {
            if (msg.sender == guardian()) {
                require(!isEnabled, "DFM: Guardian can only disable");
            } else {
                revert("DFM Not owner or guardian");
            }
        }
        _;
    }

    function owner() public view returns (address) {
        return address(CORE_OWNER.owner());
    }

    function bridgeRelay() internal view returns (address) {
        return CORE_OWNER.bridgeRelay();
    }

    function feeReceiver() internal view returns (address) {
        return CORE_OWNER.feeReceiver();
    }

    function guardian() internal view returns (address) {
        return CORE_OWNER.guardian();
    }
}
