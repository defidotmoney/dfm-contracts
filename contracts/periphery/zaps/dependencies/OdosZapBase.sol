// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { ReentrancyGuard } from "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { IMainController } from "../../../interfaces/IMainController.sol";
import { IBridgeToken } from "../../../interfaces/IBridgeToken.sol";

/**
    @title Odos Zap abstract base
    @author defidotmoney
    @notice Base logic for performing token swaps via Odos' V2 router
    @dev Used as a delegate for calls to `MainController`
 */
abstract contract OdosZapBase is ReentrancyGuard {
    using SafeERC20 for IERC20;

    IMainController public immutable mainController;
    IBridgeToken public immutable stableCoin;
    address public immutable router;

    mapping(address market => IERC20 collateral) internal _marketCollaterals;
    mapping(IERC20 token => bool isRouterApproved) internal _routerApprovals;

    /**
        @notice Contract constructor
        @param _mainController MainController contract address
        @param _stable Stablecoin token address
        @param _router Odos router address (available at https://github.com/odos-xyz/odos-router-v2)
     */
    constructor(address _mainController, address _stable, address _router) {
        mainController = IMainController(_mainController);
        stableCoin = IBridgeToken(_stable);
        router = _router;
        approveRouter(IERC20(_stable));
    }

    function approveRouter(IERC20 token) internal {
        if (!_routerApprovals[token]) {
            token.forceApprove(router, type(uint256).max);
            _routerApprovals[token] = true;
        }
    }

    function getCollateralOrRevert(address market) internal returns (IERC20) {
        IERC20 collateral = _marketCollaterals[market];
        if (address(collateral) == address(0)) {
            collateral = IERC20(mainController.get_collateral(market));
            require(address(collateral) != address(0), "DFM: Market does not exist");
            collateral.forceApprove(address(mainController), type(uint256).max);
            approveRouter(collateral);
            _marketCollaterals[market] = collateral;
        }
        return collateral;
    }

    function callRouter(bytes memory routingData, uint256 nativeAmount) internal {
        (bool success, ) = router.call{ value: nativeAmount }(routingData);
        require(success, "DFM: Odos router call failed");
    }
}
