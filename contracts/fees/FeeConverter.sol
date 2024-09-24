// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { IERC20Metadata } from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import { IMainController } from "../interfaces/IMainController.sol";
import { IBridgeToken } from "../interfaces/IBridgeToken.sol";
import { FeeConverterBase } from "./dependencies/FeeConverterBase.sol";

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

    constructor(
        address _core,
        IMainController _mainController,
        IBridgeToken _stableCoin,
        address _primaryChainFeeAggregator,
        address _wrappedNativeToken,
        uint16 _swapBonusPctBps,
        uint256 _swapMaxBonusAmount,
        uint256 _relayMinBalance,
        uint256 _relayMaxSwapDebtAmount
    )
        FeeConverterBase(
            _core,
            _mainController,
            _stableCoin,
            _primaryChainFeeAggregator,
            _wrappedNativeToken,
            _swapBonusPctBps,
            _swapMaxBonusAmount,
            _relayMinBalance,
            _relayMaxSwapDebtAmount
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
        require(!canSwapNativeForDebt(), "DFM: swapNativeForDebt first");
        amountOut = super.swapDebtForColl(outputToken, amountIn, minAmountOut);
        _transferToAggregator();
        return amountOut;
    }

    /**
        @notice Forward the balance of `stableCoin` to the fee aggregator
        @dev Also called during `swapDebtForColl`, if the system is functioning
             correctly a direct call to this function is likely not needed.
     */
    function transferToAggregator() external whenEnabled {
        require(!canSwapNativeForDebt(), "DFM: swapNativeForDebt first");
        _transferToAggregator();
    }

    // --- internal functions ---

    function _transferToAggregator() internal {
        address receiver = primaryChainFeeAggregator;
        if (receiver != address(0)) {
            stableCoin.transfer(primaryChainFeeAggregator, stableCoin.balanceOf(address(this)));
        }
    }
}
