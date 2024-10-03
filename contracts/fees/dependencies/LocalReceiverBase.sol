// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IFeeReceiver } from "../../interfaces/IFeeReceiver.sol";

/**
    @notice Local Receiver Abstract Base
    @author defidotmoney
    @dev Base logic for fee receivers deployed to the primary chain, where fees
         are received directly from `PrimaryFeeAggregator`
 */
abstract contract LocalReceiverBase is IFeeReceiver {
    address public immutable feeAggregator;

    event NotifyNewFees(uint256 amountProcessed);

    constructor(address _feeAggregator) {
        feeAggregator = _feeAggregator;
    }

    function quoteNotifyNewFees(uint256) external view virtual returns (uint256) {
        return 0;
    }

    function notifyNewFees(uint256 amount) external payable {
        require(msg.sender == feeAggregator, "DFM: Only feeAggregator");

        uint256 distributed = _notifyNewFees(amount);

        if (address(this).balance > 0) {
            (bool success, ) = msg.sender.call{ value: address(this).balance }("");
            require(success, "DFM: Gas refund transfer failed");
        }
        emit NotifyNewFees(distributed);
    }

    function _notifyNewFees(uint256 received) internal virtual returns (uint256 distributed);
}
