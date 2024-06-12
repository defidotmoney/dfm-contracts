// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "./dependencies/FeeConverterBase.sol";

/**
    @title Fee Converter
    @dev For use on primary chain (no bridging functionality)
    @author defidotmoney
    @notice Unguarded, incentivized functionality to:
             * Buy fee tokens for `stableCoin`
             * Buy `stableCoin` for native gas
             * Transfer `stableCoin` to the fee aggregator
 */
contract FeeConverter is FeeConverterBase {
    using SafeERC20 for IERC20Metadata;

    uint16 public bridgeBonusPctBps;
    uint256 public maxBridgeBonusAmount;

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
    )
        FeeConverterBase(
            _core,
            _mainController,
            _stableCoin,
            _primaryChainFeeAggregator,
            _wrappedNativeToken,
            _swapBonusPctBps,
            _maxSwapBonusAmount,
            _minRelayBalance,
            _maxRelaySwapDebtAmount
        )
    {}

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
    ) public override returns (uint256 amountOut) {
        require(!canSwapNativeForDebt(), "DFM: Swap native for debt first");
        amountOut = super.swapDebtForColl(outputToken, amountIn, minAmountOut);
        transferToAggregator();
        return amountOut;
    }

    /**
        @notice Forward the balance of `stableCoin` to the fee aggregator
        @dev Also called during `swapDebtForColl`, if the system is functioning
             correctly a direct call to this function is likely not needed.
     */
    function transferToAggregator() public {
        stableCoin.transfer(primaryChainFeeAggregator, stableCoin.balanceOf(address(this)));
    }
}
