// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/**
    @dev Contracts that receive stablecoin fees from `PrimaryFeeAggregator`
         must implement this interface.
 */
interface IFeeReceiver {
    event NotifyNewFees(uint256 amountProcessed);

    /**
        @notice Get the current native fee amount required to call `notifyNewFees`
        @dev Fee receivers that do not perform bridge actions should return zero.
        @param amount Stablecoin amount that will be sent in the notify call.
     */
    function quoteNotifyNewFees(uint256 amount) external view returns (uint256 nativeFee);

    /**
        @notice Called by the fee aggregator after sending a stablecoin
                balance to this contract.
        @dev * Must be permissioned so that only the aggregator can call.
             * Must accept a value transfer, even if there is no required amount.
             * All unused balance must be returned to `msg.sender`.
        @param amount Stablecoin amount that was sent to the contract.
     */
    function notifyNewFees(uint256 amount) external payable;
}
