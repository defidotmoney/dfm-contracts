// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { IFeeReceiver } from "../interfaces/IFeeReceiver.sol";

contract FeeReceiverMock is IFeeReceiver {
    IERC20 public immutable stableCoin;

    bool public raiseOnNotify;
    uint256 public returnAmount;

    event Notified(uint256 amount);

    constructor(IERC20 _stable) {
        stableCoin = _stable;
    }

    function notifyWeeklyFees(uint256 amount) external {
        require(!raiseOnNotify, "FeeReceiverMock: notifyWeeklyFees");

        emit Notified(amount);

        if (returnAmount > 0) {
            stableCoin.transfer(msg.sender, returnAmount);
        }
    }

    function setRaiseOnNotify(bool _raiseOnNotify) external {
        raiseOnNotify = _raiseOnNotify;
    }

    function setReturnAmount(uint256 _amount) external {
        returnAmount = _amount;
    }
}
