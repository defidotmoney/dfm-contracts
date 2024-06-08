// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/interfaces/IERC3156FlashLender.sol";
import "../../interfaces/IMainController.sol";

contract LeverageZapOdosV2 is IERC3156FlashBorrower {
    using SafeERC20 for IERC20;

    bytes32 private constant _RETURN_VALUE = keccak256("ERC3156FlashBorrower.onFlashLoan");

    IMainController public immutable mainController;
    address public immutable stableCoin;
    address public immutable router;

    mapping(address market => IERC20 collateral) marketCollaterals;

    constructor(IMainController _mainController, address _stable, address _router) {
        mainController = _mainController;
        stableCoin = _stable;
        router = _router;

        IERC20(_stable).approve(address(_mainController), type(uint256).max);
        IERC20(_stable).approve(_stable, type(uint256).max);
    }

    function _getCollateral(address market) internal returns (IERC20) {
        IERC20 collateral = marketCollaterals[market];
        if (address(collateral) == address(0)) {
            collateral = IERC20(mainController.get_collateral(market));
            collateral.safeApprove(address(mainController), type(uint256).max);
        }
        return collateral;
    }

    function close_loan(address market, uint256 debtAmount, bytes calldata routingData) external {
        IERC20 collateral = _getCollateral(market);
        IERC20(stableCoin).transferFrom(msg.sender, address(this), debtAmount);

        (int256 debtChange, uint256 collReceived) = mainController.get_close_loan_amounts(market, msg.sender);
        require(debtChange < 0);
        require(collReceived > 0);

        uint256 debtShortfall = uint256(-debtChange) - debtAmount;

        bytes memory data = abi.encode(market, msg.sender, collateral, routingData);
        IERC3156FlashLender(stableCoin).flashLoan(this, stableCoin, debtShortfall, data);

        uint256 amount = collateral.balanceOf(address(this));
        if (amount > 0) collateral.safeTransfer(msg.sender, amount);

        amount = IERC20(stableCoin).balanceOf(address(this));
        if (amount > 0) IERC20(stableCoin).transfer(msg.sender, amount);
    }

    function onFlashLoan(address caller, address, uint, uint, bytes calldata data) external returns (bytes32) {
        require(caller == address(this));

        (address market, address account, IERC20 collateral, bytes memory routingData) = abi.decode(
            data,
            (address, address, IERC20, bytes)
        );

        (, uint256 collReceived) = mainController.close_loan(market, account);

        collateral.safeApprove(router, collReceived);
        (bool success, ) = router.call(routingData);
        require(success, "Router call failed");
        collateral.safeApprove(router, 0);

        return _RETURN_VALUE;
    }
}
