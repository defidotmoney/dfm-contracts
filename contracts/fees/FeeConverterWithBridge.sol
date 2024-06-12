// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "./dependencies/FeeConverterBase.sol";

/**
    @title Fee Converter and Bridge
    @author defidotmoney
    @notice Unguarded, incentivized functionality to:
             * Buy fee tokens for `stableCoin`
             * Buy `stableCoin` for native gas
             * Bridge `stableCoin` back to the primary chain
 */
contract FeeConverterWithBridge is FeeConverterBase {
    using SafeERC20 for IERC20Metadata;

    uint32 public immutable primaryId;

    address public primaryChainFeeAggregator;
    uint16 public bridgeBonusPctBps;
    uint256 public maxBridgeBonusAmount;

    constructor(
        address _core,
        IMainController _mainController,
        IBridgeToken _stableCoin,
        address _wrappedNativeToken,
        uint16 _swapBonusPctBps,
        uint256 _maxSwapBonusAmount,
        uint256 _minRelayBalance,
        uint256 _maxRelaySwapDebtAmount,
        uint32 _primaryId,
        address _primaryChainFeeAggregator,
        uint16 _bridgeBonusPctBps,
        uint256 _maxBridgeBonusAmount
    )
        FeeConverterBase(
            _core,
            _mainController,
            _stableCoin,
            _wrappedNativeToken,
            _swapBonusPctBps,
            _maxSwapBonusAmount,
            _minRelayBalance,
            _maxRelaySwapDebtAmount
        )
    {
        primaryId = _primaryId;
        primaryChainFeeAggregator = _primaryChainFeeAggregator;
        bridgeBonusPctBps = _bridgeBonusPctBps;
        maxBridgeBonusAmount = _maxBridgeBonusAmount;
    }

    /**
        @notice The Amount of `stableCoin` received as a reward for calling `bridgeOut`
     */
    function getBridgeDebtReward() public view returns (uint256 debtReward) {
        uint256 amount = stableCoin.balanceOf(address(this));
        debtReward = (amount * bridgeBonusPctBps) / MAX_BPS;
        if (debtReward > maxBridgeBonusAmount) debtReward = maxBridgeBonusAmount;

        return debtReward;
    }

    /**
        @notice The amount of nativa gas required to call `bridgeOut`
     */
    function getBridgeDebtQuote() external view returns (uint256 nativeFee) {
        address receiver = primaryChainFeeAggregator;
        if (receiver == address(0)) return 0;
        if (canSwapNativeForDebt()) return 0;

        uint256 amount = stableCoin.balanceOf(address(this));
        uint256 bonus = (amount * bridgeBonusPctBps) / MAX_BPS;
        if (bonus > maxBridgeBonusAmount) bonus = maxBridgeBonusAmount;

        return stableCoin.quoteSimple(primaryId, receiver, amount - bonus);
    }

    // --- unguarded external functions ---

    /**
        @notice Bridge this contract's `stableCoin` balance to the fee
                receiver on the primary chain.
        @dev Only callable on non-primary chains. The caller is incentivized
             with `bridgeBonusPctBps` percent of the stables bridged, up to a
             maximum of `maxBridgeBonusAmount`.
     */
    function bridgeDebt() external payable whenEnabled {
        address receiver = primaryChainFeeAggregator;
        require(receiver != address(0), "DFM: Bridge receiver not set");
        require(!canSwapNativeForDebt(), "DFM: Swap native for debt first");

        uint256 amount = stableCoin.balanceOf(address(this));
        uint256 reward = getBridgeDebtReward();
        uint256 initial = address(this).balance - msg.value;

        stableCoin.sendSimple{ value: msg.value }(primaryId, receiver, amount - reward);
        stableCoin.transfer(msg.sender, reward);

        uint256 remaining = address(this).balance - initial;
        if (remaining > 0) {
            (bool success, ) = msg.sender.call{ value: remaining }("");
            require(success, "DFM: Transfer failed");
        }
    }

    // --- owner-only external functions ---

    /**
        @notice Set the address of the fee receiver on the primary chain.
     */
    function setPrimaryChainFeeAggregator(address _primaryChainFeeAggregator) external onlyOwner {
        primaryChainFeeAggregator = _primaryChainFeeAggregator;
    }

    /**
        @notice Set the percent of `stableCoin` paid as a bonus when calling
                `bridgeDebt`. Expressed in BPS.
     */
    function setBridgeBonusPctBps(uint16 _bridgeBonusPctBps) external onlyOwner {
        bridgeBonusPctBps = _bridgeBonusPctBps;
    }

    /**
        @notice Set the max `stableCoin` amount paid as a bonus when calling `bridgeDebt`.
     */
    function setMaxBridgeBonusAmount(uint256 _maxBridgeBonusAmount) external onlyOwner {
        maxBridgeBonusAmount = _maxBridgeBonusAmount;
    }
}
