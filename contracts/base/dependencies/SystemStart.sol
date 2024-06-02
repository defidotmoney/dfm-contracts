// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "../../interfaces/IProtocolCore.sol";

/**
    @title System Start Time
    @author Prisma Finance (with edits by defidotmoney)
    @dev Provides a unified `START_TIME` for synchronized epochs
 */
abstract contract SystemStart {
    uint256 private immutable START_TIME;

    constructor(address core) {
        START_TIME = IProtocolCore(core).START_TIME();
    }

    function getWeek() internal view returns (uint256 epoch) {
        return (block.timestamp - START_TIME) / 1 weeks;
    }

    function getDay() internal view returns (uint256 day) {
        return (block.timestamp - START_TIME) / 1 days;
    }
}
