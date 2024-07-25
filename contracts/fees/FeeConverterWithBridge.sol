// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { IERC20Metadata } from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import { IMainController } from "../interfaces/IMainController.sol";
import { IBridgeToken } from "../interfaces/IBridgeToken.sol";
import { FeeConverterBase } from "./dependencies/FeeConverterBase.sol";

/**
    @title Fee Converter
    @dev For use on non-primary chains (includes bridging functionality)
    @author defidotmoney
    @notice Unguarded, incentivized functionality to:
             * Buy fee tokens for `stableCoin`
             * Buy `stableCoin` for native gas
             * Bridge `stableCoin` back to the primary chain
 */
contract FeeConverterWithBridge is FeeConverterBase {
    using SafeERC20 for IERC20Metadata;

    uint32 public immutable primaryId;

    uint16 public bridgeBonusPctBps;
    uint128 public bridgeMaxBonusAmount;

    event BridgeDebt(
        address indexed caller,
        address indexed remoteReceiver,
        uint256 bridgeAmount,
        uint256 callerReward
    );

    event SetBridgeBonusPct(uint256 bps);
    event SetBridgeMaxBonusAmount(uint256 amount);

    constructor(
        address _core,
        IMainController _mainController,
        IBridgeToken _stableCoin,
        address _primaryChainFeeAggregator,
        address _wrappedNativeToken,
        uint16 _swapBonusPctBps,
        uint256 _swapMaxBonusAmount,
        uint256 _relayMinBalance,
        uint256 _relayMaxSwapDebtAmount,
        uint32 _primaryId,
        uint16 _bridgeBonusPctBps,
        uint128 _bridgeMaxBonusAmount
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
    {
        primaryId = _primaryId;
        bridgeBonusPctBps = _bridgeBonusPctBps;
        bridgeMaxBonusAmount = _bridgeMaxBonusAmount;
    }

    receive() external payable {}

    /**
        @notice The Amount of `stableCoin` received as a reward for calling `bridgeOut`
     */
    function getBridgeDebtReward() public view returns (uint256 debtReward) {
        uint256 amount = stableCoin.balanceOf(address(this));
        debtReward = (amount * bridgeBonusPctBps) / MAX_BPS;
        if (debtReward > bridgeMaxBonusAmount) debtReward = bridgeMaxBonusAmount;

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
        if (bonus > bridgeMaxBonusAmount) bonus = bridgeMaxBonusAmount;

        return stableCoin.quoteSimple(primaryId, receiver, amount - bonus);
    }

    // --- unguarded external functions ---

    /**
        @notice Bridge this contract's `stableCoin` balance to the fee
                receiver on the primary chain.
        @dev Only callable on non-primary chains. The caller is incentivized
             with `bridgeBonusPctBps` percent of the stables bridged, up to a
             maximum of `bridgeMaxBonusAmount`.
     */
    function bridgeDebt() external payable whenEnabled {
        address receiver = primaryChainFeeAggregator;
        require(receiver != address(0), "DFM: Bridge receiver not set");
        require(!canSwapNativeForDebt(), "DFM: swapNativeForDebt first");

        uint256 amount = stableCoin.balanceOf(address(this));
        uint256 reward = getBridgeDebtReward();
        uint256 initial = address(this).balance - msg.value;

        stableCoin.sendSimple{ value: msg.value }(primaryId, receiver, amount - reward);
        stableCoin.transfer(msg.sender, reward);

        uint256 remaining = address(this).balance - initial;
        if (remaining > 0) {
            (bool success, ) = msg.sender.call{ value: remaining }("");
            require(success, "DFM: Gas refund transfer failed");
        }
        emit BridgeDebt(msg.sender, receiver, amount - reward, reward);
    }

    // --- owner-only external functions ---

    /**
        @notice Set the percent of `stableCoin` paid as a bonus when calling
                `bridgeDebt`. Expressed in BPS.
     */
    function setBridgeBonusPctBps(uint16 _bridgeBonusPctBps) external onlyOwner {
        require(_bridgeBonusPctBps <= MAX_BPS, "DFM: pct > MAX_PCT");
        bridgeBonusPctBps = _bridgeBonusPctBps;
        emit SetBridgeBonusPct(_bridgeBonusPctBps);
    }

    /**
        @notice Set the max `stableCoin` amount paid as a bonus when calling `bridgeDebt`.
     */
    function setBridgeMaxBonusAmount(uint128 _bridgeMaxBonusAmount) external onlyOwner {
        bridgeMaxBonusAmount = _bridgeMaxBonusAmount;
        emit SetBridgeMaxBonusAmount(_bridgeMaxBonusAmount);
    }
}
