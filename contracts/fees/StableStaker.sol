// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { Math } from "@openzeppelin/contracts/utils/math/Math.sol";
import { SystemStart } from "../base/dependencies/SystemStart.sol";
import { Peer } from "../bridge/dependencies/DataStructures.sol";
import { BridgeTokenBase } from "../bridge/dependencies/BridgeTokenBase.sol";
import { IFeeReceiver } from "../interfaces/IFeeReceiver.sol";
import { IStakerRewardRegulator } from "../interfaces/IStakerRewardRegulator.sol";

/**
    @title  StableStaker: ERC4626-ish Staking Contract
    @author defidotmoney, with inspiration from:
             * ERC4626 Alliance: xERC4626
             * Ethena Labs: StakedUSDeV2
             * Zefram: xERC20
    @notice Allows users to stake stablecoins to earn a portion of protocol yield.
    @dev * This contract mostly follows the ERC4626 standard, however it breaks
           compatibility by lacking `withdraw` and `redeem` functions. Withdrawals
           are possible by calling `cooldownAssets` or `cooldownShares`, waiting
           for the `cooldownDuration` to pass, and then calling `unstake`.
         * Only deployed on the primary chain. Use `BridgeTokenSimple` as a peer
           on non-primary chains.
 */
contract StableStaker is IFeeReceiver, BridgeTokenBase, SystemStart {
    uint256 public constant maxDeposit = type(uint256).max;
    uint256 public constant maxMint = type(uint256).max;
    uint256 public constant MAX_COOLDOWN_DURATION = 4 weeks;

    IERC20 public immutable asset;
    address public feeAggregator;
    IStakerRewardRegulator public rewardRegulator;
    address public govStaker;

    uint32 public cooldownDuration;
    uint32 public lastDistributionDay;

    uint32 public lastUpdate;
    uint32 public periodFinish;
    uint256 public rewardsPerSecond;
    uint256 public lastWeeklyAmountReceived;

    uint256 public totalStoredAssets;
    uint256 public totalCooldownAssets;
    uint256 public totalMintedSupply;

    mapping(address => AssetCooldown) public cooldowns;

    struct AssetCooldown {
        uint224 underlyingAmount;
        uint32 cooldownEnd;
    }

    event Deposit(address indexed caller, address indexed owner, uint256 assets, uint256 shares);
    event Cooldown(address indexed caller, uint256 assets, uint256 shares, uint256 cooldownEnd);
    event Unstake(address indexed owner, address indexed receiver, uint256 assets);

    event NewRewardPeriod(uint256 day, uint256 total, uint256 stakerAmount, uint256 govAmount);

    event CooldownDurationUpdated(uint32 cooldownDuration);
    event FeeAggregatorSet(address feeAggregator);
    event RewardRegulatorSet(IStakerRewardRegulator regulator);
    event GovStakerSet(address govStaker);

    constructor(
        address _core,
        IERC20 _stable,
        address _feeAggregator,
        IStakerRewardRegulator _rewardRegulator,
        string memory _name,
        string memory _symbol,
        uint32 _cooldownDuration,
        address _lzEndpoint,
        bytes memory _defaultOptions,
        Peer[] memory _tokenPeers
    ) BridgeTokenBase(_core, _name, _symbol, _lzEndpoint, _defaultOptions, _tokenPeers) SystemStart(_core) {
        asset = _stable;
        feeAggregator = _feeAggregator;
        rewardRegulator = _rewardRegulator;
        cooldownDuration = _cooldownDuration;

        emit FeeAggregatorSet(_feeAggregator);
        emit CooldownDurationUpdated(_cooldownDuration);

        _setNewStream(0, 0, getDay());
    }

    // --- external view functions ---

    /**
        @notice Compute the amount of tokens available to share holders.
        @dev Increases linearly during an active reward distribution period.
     */
    function totalAssets() public view returns (uint256) {
        uint256 updateUntil = Math.min(periodFinish, block.timestamp);
        uint256 duration = updateUntil - lastUpdate;
        return totalStoredAssets + (duration * rewardsPerSecond);
    }

    function convertToShares(uint256 assets) public view returns (uint256) {
        uint256 supply = totalMintedSupply;

        return supply == 0 ? assets : Math.mulDiv(assets, supply, totalAssets(), Math.Rounding.Down);
    }

    function convertToAssets(uint256 shares) public view returns (uint256) {
        uint256 supply = totalMintedSupply;

        return supply == 0 ? shares : Math.mulDiv(shares, totalAssets(), supply, Math.Rounding.Down);
    }

    function previewDeposit(uint256 assets) public view returns (uint256) {
        return convertToShares(assets);
    }

    function previewMint(uint256 shares) public view returns (uint256) {
        uint256 supply = totalMintedSupply;

        return supply == 0 ? shares : Math.mulDiv(shares, totalAssets(), supply, Math.Rounding.Up);
    }

    function previewWithdraw(uint256 assets) public view returns (uint256) {
        uint256 supply = totalMintedSupply;

        return supply == 0 ? assets : Math.mulDiv(assets, supply, totalAssets(), Math.Rounding.Up);
    }

    function previewRedeem(uint256 shares) public view returns (uint256) {
        return convertToAssets(shares);
    }

    function maxWithdraw(address owner) public view returns (uint256) {
        return convertToAssets(balanceOf(owner));
    }

    function maxRedeem(address owner) public view returns (uint256) {
        return balanceOf(owner);
    }

    function quoteNotifyNewFees(uint256) external view returns (uint256) {
        return 0;
    }

    // --- unguarded external functions ---

    /**
        @notice Mints shares to the receiver by depositing an exact amount of underlying tokens
        @param assets Amount of assets to deposit
        @param receiver Address to mint shares to
        @return shares Amount of shares minted
     */
    function deposit(uint256 assets, address receiver) external returns (uint256 shares) {
        // Check for rounding error since we round down in previewDeposit.
        require((shares = previewDeposit(assets)) != 0, "ZERO_SHARES");
        _updateDailyStream();
        _deposit(assets, shares, receiver);
        return shares;
    }

    /**
        @notice Mints an exact amount of shares to the receiver by depositing underlying tokens
        @param shares Amount of shares to mint
        @param receiver Address to mint shares to
        @return assets Amount of assets deposited
     */
    function mint(uint256 shares, address receiver) external returns (uint256 assets) {
        _updateDailyStream();

        assets = previewMint(shares);
        _deposit(assets, shares, receiver);
        return assets;
    }

    /**
        @notice Redeem assets and start a cooldown to claim the underlying asset.
        @param assets Amount of assets to start cooldown for.
        @return shares Amount of shares redeemed.
     */
    function cooldownAssets(uint256 assets) external returns (uint256 shares) {
        _updateDailyStream();
        require(assets <= maxWithdraw(msg.sender), "sMONEY: insufficient assets");

        shares = previewWithdraw(assets);
        _cooldown(assets, shares);
        return shares;
    }

    /**
        @notice Redeem shares into assets, and start a cooldown to claim the underlying asset.
        @param shares Amount of shares to redeem.
        @return assets Amount of assets cooling down.
     */
    function cooldownShares(uint256 shares) external returns (uint256 assets) {
        _updateDailyStream();
        require(shares <= maxRedeem(msg.sender), "sMONEY: insufficient shares");

        assets = previewRedeem(shares);
        _cooldown(assets, shares);
        return assets;
    }

    /**
        @notice Claim the staked amount once the cooldown period has finished.
        @param receiver Address to send the claimed assets to.
     */
    function unstake(address receiver) external {
        AssetCooldown memory ac = cooldowns[msg.sender];
        uint256 amount = ac.underlyingAmount;
        require(amount > 0, "sMONEY: Nothing to withdraw");
        require(ac.cooldownEnd <= block.timestamp, "sMONEY: cooldown still active");

        delete cooldowns[msg.sender];
        totalCooldownAssets = totalCooldownAssets - amount;

        asset.transfer(receiver, amount);

        emit Unstake(msg.sender, receiver, amount);
    }

    // --- guarded external functions ---

    function notifyNewFees(uint256) external payable {
        require(msg.sender == feeAggregator);

        uint256 updateUntil = _advanceCurrentStream();
        uint256 residualAmount = (periodFinish - updateUntil) * rewardsPerSecond;
        uint256 weekAmount = asset.balanceOf(address(this)) - totalStoredAssets - totalCooldownAssets - residualAmount;
        lastWeeklyAmountReceived = weekAmount;

        uint256 updateDays = getDay() - (getWeek() * 7) + 1;
        uint256 newAmount = (weekAmount / 7) * updateDays;

        _setNewStream(newAmount, residualAmount, getDay());

        if (msg.value != 0) {
            (bool success, ) = msg.sender.call{ value: msg.value }("");
            require(success, "DFM: Gas refund transfer failed");
        }

        emit NotifyNewFees(weekAmount);
    }

    function setCooldownDuration(uint32 _cooldownDuration) external onlyOwner {
        require(_cooldownDuration <= MAX_COOLDOWN_DURATION, "sMONEY: Invalid duration");
        cooldownDuration = _cooldownDuration;

        emit CooldownDurationUpdated(_cooldownDuration);
    }

    function setFeeAggregator(address _feeAggregator) external onlyOwner {
        feeAggregator = _feeAggregator;

        emit FeeAggregatorSet(_feeAggregator);
    }

    function setRewardRegulator(IStakerRewardRegulator _regulator) external onlyOwner {
        rewardRegulator = _regulator;

        emit RewardRegulatorSet(_regulator);
    }

    function setGovStaker(address _govStaker) external onlyOwner {
        govStaker = _govStaker;

        emit GovStakerSet(_govStaker);
    }

    // --- internal functions ---

    /** @dev Shared logic for `deposit` and `mint` */
    function _deposit(uint256 assets, uint256 shares, address receiver) internal {
        asset.transferFrom(msg.sender, address(this), assets);

        _mint(receiver, shares);
        totalMintedSupply += shares;
        totalStoredAssets += assets;

        emit Deposit(msg.sender, receiver, assets, shares);
    }

    /** @dev Shared logic for `cooldownAssets` and `cooldownShares` */
    function _cooldown(uint256 assets, uint256 shares) internal {
        require(assets > 0, "sMONEY: zero assets");

        uint32 cooldownEnd = uint32(block.timestamp + cooldownDuration);
        cooldowns[msg.sender] = AssetCooldown({
            underlyingAmount: uint224(cooldowns[msg.sender].underlyingAmount + assets),
            cooldownEnd: cooldownEnd
        });
        totalCooldownAssets = totalCooldownAssets + assets;
        totalStoredAssets = totalStoredAssets - assets;
        totalMintedSupply -= shares;

        _burn(msg.sender, shares);

        emit Cooldown(msg.sender, assets, shares, cooldownEnd);
    }

    /**
        @dev Advance the current reward stream, and optionally update the stream
             within the current week.
    */
    function _updateDailyStream() internal {
        uint256 updateUntil = _advanceCurrentStream();

        uint256 lastUpdateDay = (lastDistributionDay / 7 + 1) * 7 - 1;
        uint256 day = Math.min(getDay(), lastUpdateDay);
        uint256 updateDays = day - lastDistributionDay;
        if (updateDays == 0) return;

        uint256 newAmount = (lastWeeklyAmountReceived / 7) * updateDays;
        uint256 residualAmount = (periodFinish - updateUntil) * rewardsPerSecond;
        _setNewStream(newAmount, residualAmount, day);
    }

    /** @dev Advance the current reward stream */
    function _advanceCurrentStream() internal returns (uint256 updateUntil) {
        updateUntil = Math.min(periodFinish, block.timestamp);
        uint256 duration = updateUntil - lastUpdate;
        if (duration > 0) {
            totalStoredAssets = totalStoredAssets + (duration * rewardsPerSecond);
            lastUpdate = uint32(updateUntil);
        }
        return updateUntil;
    }

    /** @dev Start a new reward stream period */
    function _setNewStream(uint256 newAmount, uint256 residualAmount, uint256 day) internal {
        uint256 stakerAmount = rewardRegulator.getStakerRewardAmount(newAmount);
        require(stakerAmount <= newAmount, "sMONEY: Invalid stakerAmount");

        uint256 govAmount = newAmount - stakerAmount;
        if (govAmount > 0) {
            address _govStaker = govStaker;
            asset.transfer(_govStaker, govAmount);
            IFeeReceiver(_govStaker).notifyNewFees(govAmount);
        }

        stakerAmount += residualAmount;
        rewardsPerSecond = stakerAmount / 2 days;

        lastUpdate = uint32(block.timestamp);
        periodFinish = uint32(block.timestamp + 2 days);
        lastDistributionDay = uint32(day);

        emit NewRewardPeriod(day, newAmount, stakerAmount, govAmount);
    }

    /** @dev Internal function to perform a credit operation. Inherited from `OFT`. */
    function _credit(
        address _to,
        uint256 _amountLD,
        uint32 _srcEid
    ) internal override returns (uint256 amountReceivedLD) {
        amountReceivedLD = super._credit(_to, _amountLD, _srcEid);
        require(totalSupply() <= totalMintedSupply, "DFM: Oversupply");
    }
}
