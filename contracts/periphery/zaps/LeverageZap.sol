// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/interfaces/IERC3156FlashBorrower.sol";
import "../../interfaces/IMainController.sol";
import "../../interfaces/IBridgeToken.sol";

contract LeverageZapOdosV2 is IERC3156FlashBorrower {
    using SafeERC20 for IERC20;
    using SafeERC20 for IBridgeToken;

    bytes32 private constant _RETURN_VALUE = keccak256("ERC3156FlashBorrower.onFlashLoan");

    IMainController public immutable mainController;
    IBridgeToken public immutable stableCoin;
    address public immutable router;

    enum FlashLoanAction {
        OpenLoan,
        CloseLoan
    }

    mapping(address market => IERC20 collateral) marketCollaterals;

    constructor(IMainController _mainController, IBridgeToken _stable, address _router) {
        mainController = _mainController;
        stableCoin = _stable;
        router = _router;

        _stable.approve(address(_mainController), type(uint256).max);
        _stable.approve(address(_stable), type(uint256).max);
    }

    function _getCollateral(address market) internal returns (IERC20) {
        IERC20 collateral = marketCollaterals[market];
        if (address(collateral) == address(0)) {
            collateral = IERC20(mainController.get_collateral(market));
            collateral.safeApprove(address(mainController), type(uint256).max);
            marketCollaterals[market] = collateral;
        }
        return collateral;
    }

    function open_loan(
        address market,
        uint256 debtAmount,
        uint256 collAmount,
        uint256 numBands,
        bytes calldata routingData
    ) external {
        IERC20 collateral = _getCollateral(market);
        if (collAmount > 0) collateral.safeTransferFrom(msg.sender, address(this), collAmount);

        bytes memory data = abi.encode(FlashLoanAction.OpenLoan, msg.sender, market, collateral, numBands, routingData);
        stableCoin.flashLoan(this, address(stableCoin), debtAmount, data);
    }

    function close_loan(address market, uint256 debtAmount, bytes calldata routingData) external {
        IERC20 collateral = _getCollateral(market);
        if (debtAmount > 0) stableCoin.transferFrom(msg.sender, address(this), debtAmount);

        (int256 debtChange, uint256 collReceived) = mainController.get_close_loan_amounts(msg.sender, market);
        require(debtChange < 0);
        require(collReceived > 0);

        uint256 debtShortfall = uint256(-debtChange) - debtAmount;

        bytes memory data = abi.encode(FlashLoanAction.CloseLoan, market, msg.sender, collateral, routingData);
        stableCoin.flashLoan(this, address(stableCoin), debtShortfall, data);

        uint256 amount = collateral.balanceOf(address(this));
        if (amount > 0) collateral.safeTransfer(msg.sender, amount);

        amount = stableCoin.balanceOf(address(this));
        if (amount > 0) stableCoin.transfer(msg.sender, amount);
    }

    function onFlashLoan(
        address initiator,
        address /* token */,
        uint256 amount,
        uint /* fee */,
        bytes calldata data
    ) external returns (bytes32) {
        require(msg.sender == address(stableCoin), "DFM: Invalid caller");
        require(initiator == address(this), "DFM: Invalid initiator");

        FlashLoanAction action = abi.decode(data, (FlashLoanAction));
        if (action == FlashLoanAction.OpenLoan) {
            return _flashLoanOpenLoan(amount, data);
        } else if (action == FlashLoanAction.CloseLoan) {
            return _flashLoanCloseLoan(data);
        } else {
            revert("DFM: Invalid flashloan action");
        }
    }

    function _flashLoanOpenLoan(uint256 flashloanAmount, bytes calldata data) internal returns (bytes32) {
        (, address account, address market, IERC20 collateral, uint256 numBands, bytes memory routingData) = abi.decode(
            data,
            (uint256, address, address, IERC20, uint256, bytes)
        );

        stableCoin.safeApprove(router, flashloanAmount);
        (bool success, ) = router.call(routingData);
        require(success, "DFM: Odos router call failed");
        stableCoin.safeApprove(router, 0);

        mainController.create_loan(account, market, collateral.balanceOf(address(this)), flashloanAmount, numBands);

        return _RETURN_VALUE;
    }

    function _flashLoanCloseLoan(bytes calldata data) internal returns (bytes32) {
        (, address market, address account, IERC20 collateral, bytes memory routingData) = abi.decode(
            data,
            (uint256, address, address, IERC20, bytes)
        );

        (, uint256 collReceived) = mainController.close_loan(account, market);

        collateral.safeApprove(router, collReceived);
        (bool success, ) = router.call(routingData);
        require(success, "DFM: Odos router call failed");
        collateral.safeApprove(router, 0);

        return _RETURN_VALUE;
    }
}
