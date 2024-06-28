// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/interfaces/IERC3156FlashBorrower.sol";
import "../../interfaces/IMainController.sol";
import "../../interfaces/IBridgeToken.sol";

/**
    @title Leverage Zap using Odos V2 Router
    @author defidotmoney
 */
contract LeverageZapOdosV2 is IERC3156FlashBorrower {
    using SafeERC20 for IERC20;
    using SafeERC20 for IBridgeToken;

    bytes32 private constant _RETURN_VALUE = keccak256("ERC3156FlashBorrower.onFlashLoan");

    IMainController public immutable mainController;
    IBridgeToken public immutable stableCoin;
    address public immutable router;

    enum FlashLoanAction {
        CreateLoan,
        IncreaseDebt,
        DecreaseDebt,
        CloseLoan
    }

    mapping(address market => IERC20 collateral) marketCollaterals;

    /**
        @notice Contract constructor
        @param _mainController MainController contract address
        @param _stable Stablecoin token address
        @param _router Odos router address (available at https://github.com/odos-xyz/odos-router-v2)
     */
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

    /**
        @notice Use a flashloan to create a new loan
        @dev The router swap should convert exactly `debtAmount` of stablecoin into the collateral
             for the given market. The entire received collateral balance is used to create the new
             loan. Any remaining stablecoin balance is transferred to the caller.
        @param market Address of the market to create a new loan in
        @param debtAmount Debt amount of the loan
        @param collAmount Collateral amount provided by the caller
        @param numBands Number of bands to use for the loan
        @param routingData Odos router swap calldata
     */
    function createLoan(
        address market,
        uint256 debtAmount,
        uint256 collAmount,
        uint256 numBands,
        bytes calldata routingData
    ) external {
        IERC20 collateral = _getCollateral(market);
        if (collAmount > 0) collateral.safeTransferFrom(msg.sender, address(this), collAmount);

        bytes memory data = abi.encode(
            FlashLoanAction.CreateLoan,
            msg.sender,
            market,
            collateral,
            numBands,
            routingData
        );
        stableCoin.flashLoan(this, address(stableCoin), debtAmount, data);

        uint256 amount = stableCoin.balanceOf(address(this));
        if (amount > 0) stableCoin.transfer(msg.sender, amount);
    }

    /**
        @dev The router swap should convert `debtFlashloan` of stablecoin into the collateral
             for the given market. The loan adjustment adds the entire collateral balance and
             mints the required debt to repay the flashloan. No debt or collateral is returned.
        @param market Address of the market where the loan is being adjusted
        @param debtAmount Debt amount provided by the caller
        @param debtFlashloan Debt amount to flashloan
        @param collAmount Collateral amount provided by the caller
        @param routingData Odos router swap calldata
     */
    function increaseDebt(
        address market,
        uint256 debtAmount,
        uint256 debtFlashloan,
        uint256 collAmount,
        bytes calldata routingData
    ) external {
        IERC20 collateral = _getCollateral(market);
        if (collAmount > 0) collateral.safeTransferFrom(msg.sender, address(this), collAmount);
        if (debtAmount > 0) stableCoin.transferFrom(msg.sender, address(this), debtAmount);

        bytes memory data = abi.encode(FlashLoanAction.IncreaseDebt, msg.sender, market, collateral, routingData);
        stableCoin.flashLoan(this, address(stableCoin), debtFlashloan, data);
    }

    /**
        @notice Decrease the debt of an existing loan by selling collateral
        @dev The router swap must convert up to `collAmount` of collateral into at least `debtAmount`
             of stablecoin. Any remaining debt or collateral balances are transferred to the caller.
        @param market Address of the market to close the loan in
        @param debtAmount Amount of debt to reduce the loan by
        @param collAmount Amount of collateral to withdraw from the loan
        @param routingData Odos router swap calldata
     */
    function decreaseDebt(address market, uint256 debtAmount, uint256 collAmount, bytes calldata routingData) external {
        IERC20 collateral = _getCollateral(market);

        bytes memory data = abi.encode(
            FlashLoanAction.DecreaseDebt,
            msg.sender,
            market,
            collateral,
            collAmount,
            routingData
        );
        stableCoin.flashLoan(this, address(stableCoin), debtAmount, data);

        uint256 amount = collateral.balanceOf(address(this));
        if (amount > 0) collateral.safeTransfer(msg.sender, amount);

        amount = stableCoin.balanceOf(address(this));
        if (amount > 0) stableCoin.transfer(msg.sender, amount);
    }

    /**
        @notice Close a loan by selling collateral to cover a portion of the debt
        @dev The router swap should convert enough collateral into stablecoin to cover the debt
             shortfall. Any remaining debt or collateral balances are transferred to the caller.
        @param market Address of the market to close the loan in
        @param debtAmount Debt amount provided by the caller
        @param routingData Odos router swap calldata
     */
    function closeLoan(address market, uint256 debtAmount, bytes calldata routingData) external {
        IERC20 collateral = _getCollateral(market);
        if (debtAmount > 0) stableCoin.transferFrom(msg.sender, address(this), debtAmount);

        (int256 debtChange, uint256 collReceived) = mainController.get_close_loan_amounts(msg.sender, market);
        require(debtChange < 0);
        require(collReceived > 0);

        uint256 debtShortfall = uint256(-debtChange) - debtAmount;

        bytes memory data = abi.encode(FlashLoanAction.CloseLoan, msg.sender, market, collateral, routingData);
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
        if (action == FlashLoanAction.CreateLoan) _flashLoanCreateLoan(amount, data);
        else if (action == FlashLoanAction.IncreaseDebt) _flashLoanIncreaseDebt(amount, data);
        else if (action == FlashLoanAction.CloseLoan) _flashLoanCloseLoan(data);
        else revert("DFM: Invalid flashloan action");

        return _RETURN_VALUE;
    }

    function _flashLoanCreateLoan(uint256 flashloanAmount, bytes calldata data) internal returns (bytes32) {
        (, address account, address market, IERC20 collateral, uint256 numBands, bytes memory routingData) = abi.decode(
            data,
            (uint256, address, address, IERC20, uint256, bytes)
        );

        _callRouter(stableCoin, flashloanAmount, routingData);
        mainController.create_loan(account, market, collateral.balanceOf(address(this)), flashloanAmount, numBands);
    }

    function _flashLoanIncreaseDebt(uint256 flashloanAmount, bytes calldata data) internal returns (bytes32) {
        (, address account, address market, IBridgeToken collateral, bytes memory routingData) = abi.decode(
            data,
            (uint256, address, address, IBridgeToken, bytes)
        );

        _callRouter(stableCoin, stableCoin.balanceOf(address(this)), routingData);
        int256 debtAmount = int256(flashloanAmount - stableCoin.balanceOf(address(this)));
        int256 collAmount = int256(collateral.balanceOf(address(this)));
        mainController.adjust_loan(account, market, debtAmount, collAmount);
    }

    function _flashLoanDecreaseDebt(uint256 flashloanAmount, bytes calldata data) internal returns (bytes32) {
        (, address account, address market, IBridgeToken collateral, uint256 collAmount, bytes memory routingData) = abi
            .decode(data, (uint256, address, address, IBridgeToken, uint256, bytes));

        mainController.adjust_loan(account, market, -int256(flashloanAmount), -int256(collAmount));
        _callRouter(collateral, collAmount, routingData);
    }

    function _flashLoanCloseLoan(bytes calldata data) internal returns (bytes32) {
        (, address account, address market, IBridgeToken collateral, bytes memory routingData) = abi.decode(
            data,
            (uint256, address, address, IBridgeToken, bytes)
        );

        (, uint256 collReceived) = mainController.close_loan(account, market);
        _callRouter(collateral, collReceived, routingData);
    }

    function _callRouter(IBridgeToken token, uint256 amount, bytes memory routingData) internal {
        token.safeApprove(router, amount);
        (bool success, ) = router.call(routingData);
        require(success, "DFM: Odos router call failed");
        token.safeApprove(router, 0);
    }
}
