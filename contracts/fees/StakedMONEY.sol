// SPDX-License-Identifier: MIT
// Rewards logic inspired by xERC20 (https://github.com/ZeframLou/playpen/blob/main/src/xERC20.sol)

pragma solidity 0.8.25;

import "@solmate/tokens/ERC4626.sol";
import "../base/dependencies/CoreOwnable.sol";
import "../base/dependencies/SystemStart.sol";
import "../interfaces/IFeeReceiver.sol";

/**
 @title  An xERC4626 Single Staking Contract
 @notice This contract allows users to autocompound rewards denominated in an underlying reward token.
         It is fully compatible with [ERC4626](https://eips.ethereum.org/EIPS/eip-4626) allowing for DeFi composability.
         It maintains balances using internal accounting to prevent instantaneous changes in the exchange rate.
         NOTE: an exception is at contract creation, when a reward cycle begins before the first deposit. After the first deposit, exchange rate updates smoothly.

         Operates on "cycles" which distribute the rewards surplus over the internal balance to users linearly over the remainder of the cycle window.
*/
contract StakedMONEY is IFeeReceiver, ERC4626, CoreOwnable, SystemStart {
    address public feeAggregator;

    uint16 public lastDistributionWeek;
    uint32 public lastDistributionDay;

    uint32 lastUpdate;
    uint32 periodFinish;

    uint256 rewardsPerSecond;

    /// @notice the amount of rewards distributed in a the most recent cycle.
    uint256 public lastWeeeklyAmountReceived;

    uint256 internal storedTotalAssets;
    uint256 internal totalCooldownAssets;

    uint32 public cooldownDuration;

    struct AssetCooldown {
        uint224 underlyingAmount;
        uint32 cooldownEnd;
    }

    mapping(address => AssetCooldown) public cooldowns;

    constructor(
        address _core,
        ERC20 _stable,
        address _feeAggregator
    )
        ERC4626(_stable, string.concat("Staked ", _stable.name()), string.concat("s", _stable.symbol()))
        CoreOwnable(_core)
        SystemStart(_core)
    {
        feeAggregator = _feeAggregator;
    }

    /// @notice redeem assets and starts a cooldown to claim the converted underlying asset
    /// @param assets assets to redeem
    function cooldownAssets(uint256 assets) external returns (uint256 shares) {
        _updateDailyStream();
        require(assets <= maxWithdraw(msg.sender), "sMONEY: insufficient assets");

        shares = previewWithdraw(assets);
        _cooldown(assets, shares);
        return shares;
    }

    /// @notice redeem shares into assets and starts a cooldown to claim the converted underlying asset
    /// @param shares shares to redeem
    function cooldownShares(uint256 shares) external returns (uint256 assets) {
        _updateDailyStream();
        require(shares <= maxRedeem(msg.sender), "sMONEY: insufficient shares");

        assets = previewRedeem(shares);
        _cooldown(assets, shares);
        return assets;
    }

    function _cooldown(uint256 assets, uint256 shares) internal {
        require(assets > 0, "sMONEY: zero assets");

        cooldowns[msg.sender].cooldownEnd = uint32(block.timestamp + cooldownDuration);
        cooldowns[msg.sender].underlyingAmount = uint224(cooldowns[msg.sender].underlyingAmount + assets);
        totalCooldownAssets = totalCooldownAssets + assets;
        storedTotalAssets = storedTotalAssets - assets;

        _burn(msg.sender, shares);

        // TODO event
    }

    function unstake(address receiver) external {
        AssetCooldown memory ac = cooldowns[msg.sender];
        uint256 amount = ac.underlyingAmount;
        require(amount > 0, "sMONEY: Nothing to withdraw");
        require(ac.cooldownEnd <= block.timestamp, "sMONEY: cooldown still active");

        delete cooldowns[msg.sender];
        totalCooldownAssets = totalCooldownAssets - amount;

        asset.transfer(receiver, amount);

        // TODO event
    }

    /// @notice Compute the amount of tokens available to share holders.
    ///         Increases linearly during a reward distribution period from the sync call, not the cycle start.
    function totalAssets() public view override returns (uint256) {
        uint256 updateUntil = min(periodFinish, block.timestamp);
        uint256 duration = updateUntil - lastUpdate;
        return storedTotalAssets + (duration * rewardsPerSecond);
    }

    // Update storedTotalAssets on withdraw/redeem
    function beforeWithdraw(uint256 amount, uint256 shares) internal virtual override {
        super.beforeWithdraw(amount, shares);
        _updateDailyStream();
        storedTotalAssets -= amount;
    }

    // Update storedTotalAssets on deposit/mint
    function afterDeposit(uint256 amount, uint256 shares) internal virtual override {
        storedTotalAssets += amount;
        _updateDailyStream();
        super.afterDeposit(amount, shares);
    }

    /// @notice Distributes rewards to xERC4626 holders.
    /// All surplus `asset` balance of the contract over the internal balance becomes queued for the next cycle.
    function notifyWeeklyFees(uint256) public virtual {
        require(msg.sender == feeAggregator);

        uint256 updateUntil = _advanceCurrentStream();
        uint256 residualAmount = (periodFinish - updateUntil) * rewardsPerSecond;
        uint256 newAmount = asset.balanceOf(address(this)) - storedTotalAssets - totalCooldownAssets - residualAmount;
        lastWeeeklyAmountReceived = newAmount;
        _setNewStream(newAmount, residualAmount);
    }

    function _updateDailyStream() internal {
        uint256 updateUntil = _advanceCurrentStream();

        uint256 updateDays = getDay() - lastDistributionDay;
        if (updateDays == 0) return;

        // only `notifyWeeklyFees` can update us across weeks
        if (getDay() / 7 > lastDistributionWeek) return;

        uint256 newAmount = (lastWeeeklyAmountReceived / 7) * updateDays;
        uint256 residualAmount = (periodFinish - updateUntil) * rewardsPerSecond;
        _setNewStream(newAmount, residualAmount);
    }

    function _advanceCurrentStream() internal returns (uint256 updateUntil) {
        updateUntil = min(periodFinish, block.timestamp);
        uint256 duration = updateUntil - lastUpdate;
        if (duration > 0) {
            storedTotalAssets = storedTotalAssets + (duration * rewardsPerSecond);
            lastUpdate = uint32(updateUntil);
        }
        return updateUntil;
    }

    function _setNewStream(uint256 newAmount, uint256 residualAmount) internal {
        // TODO only retain a portion of newAmount, rest forwards onward

        newAmount += residualAmount;
        rewardsPerSecond = newAmount / 2 days;

        lastUpdate = uint32(block.timestamp);
        periodFinish = uint32(block.timestamp + 2 days);
        lastDistributionDay = uint32(getDay());
    }

    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}
