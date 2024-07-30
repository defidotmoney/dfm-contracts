// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IMarketOperator {
    function debt(address account) external view returns (uint256);
}
