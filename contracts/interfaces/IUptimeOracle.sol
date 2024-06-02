// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/**
    @dev Uptime oracles (related to L2 sequencer uptime) must implement all
         functions outlined within this interface
 */
interface IUptimeOracle {
    function getUptimeStatus() external view returns (bool);
}
