// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { ReentrancyGuard } from "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { IMainController } from "../../interfaces/IMainController.sol";

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
        uint256 debtAmount,
        uint256 numBands,
        InputAction calldata inputAction,
        OutputAction calldata outputAction
    ) external payable nonReentrant {
        _executeInputAction(inputAction);
        IERC20 collateral = _getCollateralOrRevert(market);
        uint256 collAmount = collateral.balanceOf(address(this));
        mainController.create_loan(msg.sender, market, collAmount, debtAmount, numBands);
        _executeOutputAction(outputAction);
    }

    function adjustLoan(
        address market,
        uint256 collWithdrawal,
        uint256 debtIncrease,
        InputAction calldata inputAction,
        OutputAction calldata outputAction
    ) external payable nonReentrant {
        _executeInputAction(inputAction);
        IERC20 collateral = _getCollateralOrRevert(market);

        int256 collAdjustment;
        if (collWithdrawal > 0) collAdjustment = -int256(collWithdrawal);
        else collAdjustment = int256(collateral.balanceOf(address(this)));

        int256 debtAdjustment;
        if (debtIncrease > 0) debtAdjustment = int256(debtAdjustment);
        else debtAdjustment = -(int256(stableCoin.balanceOf(address(this))));

        mainController.adjust_loan(msg.sender, market, collAdjustment, debtAdjustment);
        _executeOutputAction(outputAction);
    }

    function closeLoan(
        address market,
        InputAction calldata inputAction,
        OutputAction calldata outputAction
    ) external payable nonReentrant {
        _executeInputAction(inputAction);
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
