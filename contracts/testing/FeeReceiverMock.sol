// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { IFeeReceiver } from "../interfaces/IFeeReceiver.sol";

contract FeeReceiverMock is IFeeReceiver {
    IERC20 public immutable stableCoin;

    bool public raiseOnNotify;
    uint256 public returnAmount;
    uint256 public nativeFee;

    event Notified(uint256 amount);

    constructor(IERC20 _stable) {
        stableCoin = _stable;
    }

    function quoteNotifyNewFees(uint256 amount) external view returns (uint256) {
        return nativeFee;
    }

    function notifyNewFees(uint256 amount) external payable {
        require(!raiseOnNotify, "FeeReceiverMock: notifyNewFees");
        require(msg.value >= nativeFee, "FeeReceiverMock: nativeFee");

        emit Notified(amount);

        if (returnAmount > 0) {
            stableCoin.transfer(msg.sender, returnAmount);
        }
        if (msg.value > nativeFee) {
            (bool success, ) = msg.sender.call{ value: msg.value - nativeFee }("");
            require(success, "FeeReceiverMock: refund failed");
        }
    }

    function setRaiseOnNotify(bool _raiseOnNotify) external {
        raiseOnNotify = _raiseOnNotify;
    }

    function setReturnAmount(uint256 _amount) external {
        returnAmount = _amount;
    }

    function setNativeFee(uint256 amount) external {
        nativeFee = amount;
    }
}
