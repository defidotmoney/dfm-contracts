// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/**
    @dev Price oracles must implement all functions outlined within this interface
 */
interface IPriceOracle {
    /**
        @notice Returns the current oracle price, normalized to 1e18 precision
        @dev Called by all state-changing market / amm operations with the exception
             of `MainController.close_loan`
     */
    function price_w() external returns (uint256);

    /**
        @notice Returns the current oracle price, normalized to 1e18 precision
        @dev Read-only version used within view methods. Should always return
             the same value as `price_w`
     */
    function price() external view returns (uint256);
}
