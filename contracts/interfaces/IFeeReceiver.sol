// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/**
    @dev Contracts that receive stablecoin fees from `PrimaryFeeAggregator`
         must implement this interface.
 */
interface IFeeReceiver {
    /**
        @notice Called by the fee aggregator after sending a stablecoin
                balance to this contract.
        @dev Should be permissioned so that only the aggregator can call.
        @param amount Stablecoin amount that was sent to the contract.
     */
    function notifyWeeklyFees(uint256 amount) external;
}
