// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IVotium {
    /**
        @dev Deposit same token to multiple gauges with different amounts in
             active round with no max and no exclusions
     */
    function depositUnevenSplitGaugesSimple(
        address _token,
        address[] memory _gauges,
        uint256[] memory _amounts
    ) external;
}
