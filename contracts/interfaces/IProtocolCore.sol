// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IProtocolCore {
    function owner() external view returns (address);

    function START_TIME() external view returns (uint256);

    function getAddress(bytes32 identifier) external view returns (address);

    function bridgeRelay() external view returns (address);

    function feeReceiver() external view returns (address);

    function guardian() external view returns (address);
}
