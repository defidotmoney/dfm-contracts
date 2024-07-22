// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { CoreOwnable } from "../../base/dependencies/CoreOwnable.sol";

/**
    @title Token Recovery Abstract Base
    @author defidotmoney
    @dev Standard logic for arbitrary approval or transfer of ERC20 balances held by a contract.
 */
abstract contract TokenRecovery is CoreOwnable {
    using SafeERC20 for IERC20;

    constructor(address core) CoreOwnable(core) {}

    function transferToken(IERC20 token, address receiver, uint256 amount) external onlyOwner {
        token.safeTransfer(receiver, amount);
    }

    function setTokenApproval(IERC20 token, address spender, uint256 amount) external onlyOwner {
        token.forceApprove(spender, amount);
    }
}
