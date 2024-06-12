// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "../../base/dependencies/CoreOwnable.sol";
import "../../interfaces/IMainController.sol";
import "../../interfaces/IBridgeToken.sol";

/**
    @title Fee Converter Abstract Base
    @author defidotmoney
    @notice Unguarded, incentivized functionality to:
             * Buy fee tokens for `stableCoin`
             * Buy `stableCoin` for native gas
 */
abstract contract FeeConverterBase is CoreOwnable {
    using SafeERC20 for IERC20Metadata;

    uint256 internal constant MAX_BPS = 10000;
    IMainController public immutable mainController;
    IBridgeToken public immutable stableCoin;
    address public immutable wrappedNativeToken;
    address public primaryChainFeeAggregator;

    bool public isEnabled;

    uint16 public swapBonusPctBps;
    uint256 public maxSwapBonusAmount;
    uint256 public minRelayBalance;
    uint256 public maxRelaySwapDebtAmount;

    constructor(
        address _core,
        IMainController _mainController,
        IBridgeToken _stableCoin,
        address _primaryChainFeeAggregator,
        address _wrappedNativeToken,
        uint16 _swapBonusPctBps,
        uint256 _maxSwapBonusAmount,
        uint256 _minRelayBalance,
        uint256 _maxRelaySwapDebtAmount
    ) CoreOwnable(_core) {
        mainController = _mainController;
        stableCoin = _stableCoin;
        primaryChainFeeAggregator = _primaryChainFeeAggregator;
        wrappedNativeToken = _wrappedNativeToken;

        swapBonusPctBps = _swapBonusPctBps;
        maxSwapBonusAmount = _maxSwapBonusAmount;
        minRelayBalance = _minRelayBalance;
        maxRelaySwapDebtAmount = _maxRelaySwapDebtAmount;

        isEnabled = true;
    }

    modifier whenEnabled() {
        require(isEnabled, "DFM: Actions are disabled");
        _;
    }

    // --- external view functions ---

    /**
        @notice Get the amount received when swapping `stableCoin` for `outputToken`
        @param outputToken Address of the token to purchase
        @param debtAmountIn Stablecoin amount provided for the swap
        @return collAmountOut Amount of `outputToken` received in the swap
     */
    function getSwapDebtForCollAmountOut(
        IERC20Metadata outputToken,
        uint256 debtAmountIn
    ) public view returns (uint256 collAmountOut) {
        uint256 precision = 10 ** outputToken.decimals();
        uint256 price = mainController.get_oracle_price(address(outputToken));
        uint256 bonus = (debtAmountIn * swapBonusPctBps) / MAX_BPS;
        if (bonus > maxSwapBonusAmount) bonus = maxSwapBonusAmount;
        return _debtToColl(debtAmountIn + bonus, price, precision);
    }

    /**
        @notice Get the amount of `outputToken` needed to swap for an amount of `stableCoin`
        @dev Exact amount in might vary slightly due to rounding imprecision
        @param outputToken Address of the token to purchase
        @param collAmountOut Amount of `outputToken` to receive in the swap
        @return debtAmountIn Stablecoin amount required for the swap
     */
    function getSwapDebtForCollAmountIn(
        IERC20Metadata outputToken,
        uint256 collAmountOut
    ) external view returns (uint256 debtAmountIn) {
        uint256 precision = 10 ** outputToken.decimals();
        uint256 price = mainController.get_oracle_price(address(outputToken));
        uint256 discount = collAmountOut - ((collAmountOut * MAX_BPS) / (MAX_BPS + swapBonusPctBps));
        if (_collToDebt(discount, price, precision) > maxSwapBonusAmount) {
            discount = _debtToColl(maxSwapBonusAmount, price, precision);
        }
        return _collToDebt(collAmountOut - discount, price, precision);
    }

    /**
        @notice Check if a call to `swapNativeForDebt` is currently allowed
        @dev Only possible when the relay is configured within the core owner,
             and the relay's current balance is less than `minRelayBalance`
     */
    function canSwapNativeForDebt() public view returns (bool) {
        address relay = bridgeRelay();
        if (relay == address(0)) return false;
        if (relay.balance >= minRelayBalance) return false;
        return true;
    }

    /**
        @notice Get the amount received when swapping native gas for `stableCoin`
        @param nativeAmountIn Native gas amount provided for the swap
        @return debtAmountOut Amount of `stableCoin` received in the swap
     */
    function getSwapNativeForDebtAmountOut(uint256 nativeAmountIn) public view returns (uint256 debtAmountOut) {
        if (!canSwapNativeForDebt()) return 0;
        uint256 price = mainController.get_oracle_price(wrappedNativeToken);
        uint256 bonus = (nativeAmountIn * swapBonusPctBps) / MAX_BPS;
        debtAmountOut = _collToDebt(nativeAmountIn + bonus, price, 1e18);
        if (debtAmountOut > maxRelaySwapDebtAmount) return 0;
        return debtAmountOut;
    }

    /**
        @notice Get the amount of native gas needed to swap for an amount of `stableCoin`
        @dev Exact amount in might vary slightly due to rounding imprecision
        @param debtAmountOut Amount of `stableCoin` to receive in the swap
        @return nativeAmountIn Native gas amount required for the swap
     */
    function getSwapNativeForDebtAmountIn(uint256 debtAmountOut) external view returns (uint256 nativeAmountIn) {
        if (!canSwapNativeForDebt()) return 0;
        if (debtAmountOut > maxRelaySwapDebtAmount) return 0;
        uint256 price = mainController.get_oracle_price(wrappedNativeToken);
        uint256 discount = debtAmountOut - ((debtAmountOut * MAX_BPS) / (MAX_BPS + swapBonusPctBps));
        return _debtToColl(debtAmountOut - discount, price, 1e18);
    }

    // --- unguarded external functions ---

    /**
        @notice Purchase `outputToken` using `stableCoin`
        @dev Swaps are priced using the internal oracle within defi.money,
             with a discount applied to make it attractive for arbitrageurs.
        @param outputToken Address of the token to swap for
        @param amountIn Amount of `stableCoin` to provide for the swap
        @param minAmountOut Minimum amount of `outputToken` to receive
        @return amountOut Actual amount of `outputToken` received
     */
    function swapDebtForColl(
        IERC20Metadata outputToken,
        uint256 amountIn,
        uint256 minAmountOut
    ) public virtual whenEnabled returns (uint256 amountOut) {
        amountOut = getSwapDebtForCollAmountOut(outputToken, amountIn);
        require(amountOut >= minAmountOut, "DFM: Slippage");
        stableCoin.transferFrom(msg.sender, address(this), amountIn);
        outputToken.safeTransfer(msg.sender, amountOut);
        return amountOut;
    }

    /**
        @notice Purchase `stableCoin` using native gas tokens
        @dev Native gas is sent to the bridge relay to fund protocol
             bridge messages. The swap is only possible when the bridge
             has less than `minRelayBalance`, and then only for up to
             `maxRelaySwapDebtAmount` in `stableCoin`.
        @param amountIn Amount of native gas token in. Must be the same
                        amount that is sent in the call.
        @param minAmountOut Minimum amount of `stableCoin` to receive
        @return amountOut Actual amount of `stableCoin` received
     */
    function swapNativeForDebt(
        uint256 amountIn,
        uint256 minAmountOut
    ) external payable whenEnabled returns (uint256 amountOut) {
        require(msg.value == amountIn, "DFM: msg.value != amountIn");
        amountOut = getSwapNativeForDebtAmountOut(amountIn);
        require(amountOut != 0, "DFM: Would receive 0");
        require(amountOut >= minAmountOut, "DFM: Slippage");

        (bool success, ) = bridgeRelay().call{ value: address(this).balance }("");
        require(success, "DFM: Transfer to relay failed");

        stableCoin.transfer(msg.sender, amountOut);
        return amountOut;
    }

    // --- owner-only external functions ---

    /**
        @notice Enable or disable swaps and bridging
     */
    function setIsEnabled(bool _isEnabled) external onlyOwner {
        isEnabled = _isEnabled;
    }

    /**
        @notice Set the address of the fee aggregator on the primary chain.
        @dev The aggregator receives converted protocol fees from all chains.
     */
    function setPrimaryChainFeeAggregator(address _primaryChainFeeAggregator) external onlyOwner {
        primaryChainFeeAggregator = _primaryChainFeeAggregator;
    }

    /**
        @notice Set the bonus percent of collateral received when calling
                `swapDebtForColl` or `swapNativeForDebt`. Expressed in BPS.
     */
    function setSwapBonusPctBps(uint16 _swapBonusPctBps) external onlyOwner {
        require(_swapBonusPctBps <= MAX_BPS, "DFM: pct > MAX_PCT");
        swapBonusPctBps = _swapBonusPctBps;
    }

    /**
        @notice Set the maximum amount of additional collateral received,
                when calling `swapDebtForColl` or `swapNativeForDebt`, expressed
                as an equivalent amount of `stableCoin`.
     */
    function setMaxSwapBonusAmount(uint256 _maxSwapBonusAmount) external onlyOwner {
        maxSwapBonusAmount = _maxSwapBonusAmount;
    }

    /**
        @notice Set the minimum required native gas balance in the bridge relay.
                Calls to `swapNativeForDebt` are only possible when the balance
                goes below this amount.
     */
    function setMinRelayBalance(uint256 _minRelayBalance) external onlyOwner {
        minRelayBalance = _minRelayBalance;
    }

    /**
        @notice Set the max `stableCoin` amount to receive when calling `swapNativeForDebt`.
     */
    function setMaxRelaySwapDebtAmount(uint256 _maxRelaySwapDebtAmount) external onlyOwner {
        maxRelaySwapDebtAmount = _maxRelaySwapDebtAmount;
    }

    function transferToken(IERC20Metadata token, address receiver, uint256 amount) external onlyOwner {
        token.safeTransfer(receiver, amount);
    }

    function setTokenApproval(IERC20Metadata token, address spender, uint256 amount) external onlyOwner {
        token.forceApprove(spender, amount);
    }

    // --- internal functions ---

    function _debtToColl(uint256 amount, uint256 price, uint256 precision) internal pure returns (uint256) {
        return (amount * precision) / price;
    }

    function _collToDebt(uint256 amount, uint256 price, uint256 precision) internal pure returns (uint256) {
        return (amount * price) / precision;
    }
}
