// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface ICoreOwner {
    function owner() external view returns (address);

    function START_TIME() external view returns (uint256);

    function EPOCH_LENGTH() external view returns (uint256);

    function getAddress(bytes32 identifier) external view returns (address);
}
