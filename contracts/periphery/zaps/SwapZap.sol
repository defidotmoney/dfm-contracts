// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { ReentrancyGuard } from "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { IMainController } from "../../interfaces/IMainController.sol";
import { IMarketOperator } from "../../interfaces/IMarketOperator.sol";

/**
    @title Swap Zap using Odos V2 Router
    @author defidotmoney
    @notice
    @dev Used as a delegate for calls to `MainController`
 */
contract SwapZapOdosV2 is ReentrancyGuard {
    using SafeERC20 for IERC20;

    IMainController public immutable mainController;
    IERC20 public immutable stableCoin;
    address public immutable router;

    mapping(address market => IERC20 collateral) private marketCollaterals;
    mapping(IERC20 token => bool isRouterApproved) private routerApprovals;

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
    constructor(IMainController _mainController, IERC20 _stable, address _router) {
        mainController = _mainController;
        stableCoin = _stable;
        router = _router;
        _approveRouter(_stable);
    }

    receive() external payable {}

    function createLoan(
        address market,
        uint256 collAmount,
        uint256 debtAmount,
        uint256 numBands,
        InputAction calldata inputAction,
        OutputAction calldata outputAction
    ) external payable nonReentrant {
        _executeInputAction(inputAction);
        IERC20 collateral = _getCollateralOrRevert(market);
        if (collAmount == type(uint256).max) collAmount = collateral.balanceOf(address(this));
        mainController.create_loan(msg.sender, market, collAmount, debtAmount, numBands);
        _executeOutputAction(outputAction);
    }

    function adjustLoan(
        address market,
        int256 collAdjustment,
        int256 debtAdjustment,
        InputAction calldata inputAction,
        OutputAction calldata outputAction
    ) external payable nonReentrant {
        _executeInputAction(inputAction);
        IERC20 collateral = _getCollateralOrRevert(market);

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
        @param maxDebtAmount Max stablecoin balance to be transferred from the caller
            to repay the loan. The actual amount is the difference between the owed
            amount and the zap's balance after executing `inputAction` (if any).
     */
    function closeLoan(
        address market,
        uint256 maxDebtAmount,
        InputAction calldata inputAction,
        OutputAction calldata outputAction
    ) external payable nonReentrant {
        _getCollateralOrRevert(market);
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
            _approveRouter(token);
        }
        if (inputAction.routingData.length > 0) _callRouter(inputAction.routingData, msg.value);
        else require(msg.value == 0, "DFM: msg.value > 0");
    }

    function _executeOutputAction(OutputAction calldata outputAction) internal {
        if (outputAction.routingData.length > 0) _callRouter(outputAction.routingData, 0);

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

    function _approveRouter(IERC20 token) internal {
        if (!routerApprovals[token]) {
            token.forceApprove(router, type(uint256).max);
            routerApprovals[token] = true;
        }
    }

    function _getCollateralOrRevert(address market) internal returns (IERC20) {
        IERC20 collateral = marketCollaterals[market];
        if (address(collateral) == address(0)) {
            collateral = IERC20(mainController.get_collateral(market));
            require(address(collateral) != address(0), "DFM: Market does not exist");
            collateral.forceApprove(address(mainController), type(uint256).max);
            _approveRouter(collateral);
            marketCollaterals[market] = collateral;
        }
        return collateral;
    }

    function _callRouter(bytes memory routingData, uint256 nativeAmount) internal {
        (bool success, ) = router.call{ value: nativeAmount }(routingData);
        require(success, "DFM: Odos router call failed");
    }
}
