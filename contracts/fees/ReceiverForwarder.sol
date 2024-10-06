// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { LocalReceiverBase } from "./dependencies/LocalReceiverBase.sol";
import { TokenRecovery } from "./dependencies/TokenRecovery.sol";

/**
    @notice Fee Forwarder
    @author defidotmoney
    @dev Receives fees from `PrimaryFeeAggregator` and transfers them to another address
 */
contract ForwarderFeeReceiver is LocalReceiverBase, TokenRecovery {
    IERC20 public immutable stableCoin;
    address public receiver;

    event ReceiverSet(address receiver);

    constructor(
        address core,
        address _stable,
        address _feeAggregator,
        address _receiver
    ) LocalReceiverBase(_feeAggregator) TokenRecovery(core) {
        stableCoin = IERC20(_stable);
        _setReceiver(_receiver);
    }

    function _notifyNewFees(uint256) internal override returns (uint256) {
        uint256 total = stableCoin.balanceOf(address(this));
        stableCoin.transfer(receiver, total);
    }

    function setReceiver(address _receiver) external onlyOwner {
        _setReceiver(_receiver);
    }

    function _setReceiver(address _receiver) internal {
        require(_receiver != address(0), "DFM: cannot unset receiver");
        receiver = _receiver;

        emit ReceiverSet(_receiver);
    }
}
