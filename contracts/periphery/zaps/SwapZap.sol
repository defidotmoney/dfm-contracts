// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { IMarketOperator } from "../../interfaces/IMarketOperator.sol";
import { OdosZapBase } from "./dependencies/OdosZapBase.sol";

/**
    @title Swap Zap using Odos V2 Router
    @author defidotmoney
    @dev Used as a delegate for calls to `MainController`
    @notice
        Each external function executes with the following sequence:
          1. Tokens and amounts in `InputAction.tokenAmounts` are transferred from the caller to the zap.
          2. Optionally, one or more tokens are swapped by calling Odos with `InputAction.routingData`
          3. Function-specific logic executes.
          4. Optionally, one or more tokens are swapped by calling Odos with `OutputAction.routingData`
          5. Tokens in `OutputAction.tokens` are transferred from the zap back to the caller.

        Considerations:
         * Unless otherwise indicated, token balances are not transferred to or from the zap except
           via `InputAction` and `OutputAction`. It is the responsibility of the caller to include
           all expected output tokens within `OutputAction.tokens`, including `stableCoin` and the
           market's collateral.
         * Native gas sent in the call is included in the call to Odos. Any balance held by the
           router is sent to the caller after the `OutputAction` swap.
 */
contract SwapZap is OdosZapBase {
    using SafeERC20 for IERC20;

    struct TokenAmount {
        IERC20 token;
        uint256 amount;
    }

    struct InputAction {
        TokenAmount[] tokenAmounts;
        bytes routingData;
    }

    struct OutputAction {
        IERC20[] tokens;
        bytes routingData;
    }

    /**
        @notice Contract constructor
        @param _mainController MainController contract address
        @param _stable Stablecoin token address
        @param _router Odos router address (available at https://github.com/odos-xyz/odos-router-v2)
     */
    constructor(
        address _mainController,
        address _stable,
        address _router
    ) OdosZapBase(_mainController, _stable, _router) {}

    receive() external payable {}

    /**
        @notice Create a new loan for the caller
        @param market Address of the market to create a new loan in
        @param collAmount Collateral amount to deposit
        @param debtAmount Amount of stablecoins to mint when opening the loan
        @param numBands Number of bands to use for the loan
        @param inputAction Array of token balances to transfer from the caller to the zap, and
            optional Odos router calldata. See the top-level natspec for detailed information.
        @param outputAction Array of tokens to transfer from the zap to the caller, and optional
            Odos router calldata. See the top-level natspec for detailed information.
     */
    function createLoan(
        address market,
        uint256 collAmount,
        uint256 debtAmount,
        uint256 numBands,
        InputAction calldata inputAction,
        OutputAction calldata outputAction
    ) external payable nonReentrant {
        _executeInputAction(inputAction);
        IERC20 collateral = getCollateralOrRevert(market);
        if (collAmount == type(uint256).max) collAmount = collateral.balanceOf(address(this));
        mainController.create_loan(msg.sender, market, collAmount, debtAmount, numBands);
        _executeOutputAction(outputAction);
    }

    /**
        @notice Adjust the caller's existing loan within a market
        @param market Address of the market to adjust the loan in
        @param collAdjustment Collateral adjustment amount. A positive value deposits, negative withdraws.
        @param debtAdjustment Debt adjustment amount. A positive value mints, negative burns.
        @param inputAction Array of token balances to transfer from the caller to the zap, and
            optional Odos router calldata. See the top-level natspec for detailed information.
        @param outputAction Array of tokens to transfer from the zap to the caller, and optional
            Odos router calldata. See the top-level natspec for detailed information.
     */
    function adjustLoan(
        address market,
        int256 collAdjustment,
        int256 debtAdjustment,
        InputAction calldata inputAction,
        OutputAction calldata outputAction
    ) external payable nonReentrant {
        _executeInputAction(inputAction);
        IERC20 collateral = getCollateralOrRevert(market);

        if (collAdjustment == type(int256).max) {
            collAdjustment = int256(collateral.balanceOf(address(this)));
        }

        if (debtAdjustment == type(int256).min) {
            debtAdjustment = -(int256(stableCoin.balanceOf(address(this))));
        }

        mainController.adjust_loan(msg.sender, market, collAdjustment, debtAdjustment);
        _executeOutputAction(outputAction);
    }

    /**
        @notice Close the caller's open loan within a market
        @param market Market where the loan is being closed
        @param maxDebtAmount Max stablecoin balance to be transferred from the caller
            to repay the loan. The actual amount is the difference between the owed
            amount and the zap's balance after executing `inputAction` (if any).
        @param inputAction Array of token balances to transfer from the caller to the zap, and
            optional Odos router calldata. See the top-level natspec for detailed information.
        @param outputAction Array of tokens to transfer from the zap to the caller, and optional
            Odos router calldata. See the top-level natspec for detailed information.
     */
    function closeLoan(
        address market,
        uint256 maxDebtAmount,
        InputAction calldata inputAction,
        OutputAction calldata outputAction
    ) external payable nonReentrant {
        getCollateralOrRevert(market);
        _executeInputAction(inputAction);

        if (maxDebtAmount > 0) {
            uint256 debtOwed = IMarketOperator(market).debt(msg.sender);
            uint256 balance = stableCoin.balanceOf(address(this));
            if (debtOwed > balance) {
                uint256 amount = debtOwed - balance;
                if (amount > maxDebtAmount) amount = maxDebtAmount;
                stableCoin.transferFrom(msg.sender, address(this), amount);
            }
        }
        mainController.close_loan(msg.sender, market);
        _executeOutputAction(outputAction);
    }

    function _executeInputAction(InputAction calldata inputAction) internal {
        uint256 length = inputAction.tokenAmounts.length;
        for (uint256 i = 0; i < length; i++) {
            IERC20 token = inputAction.tokenAmounts[i].token;
            token.safeTransferFrom(msg.sender, address(this), inputAction.tokenAmounts[i].amount);
            approveRouter(token);
        }
        if (inputAction.routingData.length > 0) callRouter(inputAction.routingData, msg.value);
        else require(msg.value == 0, "DFM: msg.value > 0");
    }

    function _executeOutputAction(OutputAction calldata outputAction) internal {
        if (outputAction.routingData.length > 0) callRouter(outputAction.routingData, 0);

        uint256 length = outputAction.tokens.length;
        for (uint256 i = 0; i < length; i++) {
            IERC20 token = outputAction.tokens[i];
            uint256 amount = token.balanceOf(address(this));
            if (amount > 0) token.safeTransfer(msg.sender, amount);
        }
        if (address(this).balance > 0) {
            (bool success, ) = msg.sender.call{ value: address(this).balance }("");
            require(success, "DFM: Transfer failed");
        }
    }
}
