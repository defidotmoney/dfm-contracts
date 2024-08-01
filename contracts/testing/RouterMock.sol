// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
    @notice Mock router for testing leverage zap
    @dev Contract should be funded with tokens prior to calling `mockSwap`
 */
contract RouterMock {
    using SafeERC20 for IERC20;

    struct TokenAmount {
        IERC20 token;
        uint256 amount;
    }

    receive() external payable {}

    function mockSwap(IERC20 tokenIn, IERC20 tokenOut, uint256 amountIn, uint256 amountOut) external payable {
        _transferIn(tokenIn, amountIn);
        _transferOut(tokenOut, amountOut);
    }

    function mockSwapMulti(TokenAmount[] calldata inputData, TokenAmount[] calldata outputData) external payable {
        for (uint256 i = 0; i < inputData.length; i++) {
            _transferIn(inputData[i].token, inputData[i].amount);
        }
        for (uint256 i = 0; i < outputData.length; i++) {
            _transferOut(outputData[i].token, outputData[i].amount);
        }
    }

    function _transferIn(IERC20 token, uint256 amount) internal {
        if (address(token) == address(0)) {
            require(amount == msg.value, "RouterMock: Incorrect msg.value");
        } else {
            token.safeTransferFrom(msg.sender, address(this), amount);
        }
    }

    function _transferOut(IERC20 token, uint256 amount) internal {
        if (address(token) == address(0)) {
            (bool success, ) = msg.sender.call{ value: amount }("");
            require(success, "RouterMock: Native transfer failed");
        } else {
            token.safeTransfer(msg.sender, amount);
        }
    }
}
