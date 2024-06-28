// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
    @notice Mock router for testing leverage zap
    @dev Contract should be funded with tokens prior to calling `mockSwap`
 */
contract RouterMock {
    function mockSwap(IERC20 tokenIn, IERC20 tokenOut, uint256 amountIn, uint256 amountOut) external {
        tokenIn.transferFrom(msg.sender, address(this), amountIn);
        tokenOut.transfer(msg.sender, amountOut);
    }
}
