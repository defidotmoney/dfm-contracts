// SPDX-License-Identifier: MIT
// Rewards logic inspired by xERC20 (https://github.com/ZeframLou/playpen/blob/main/src/xERC20.sol)

pragma solidity 0.8.25;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";
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
contract StakedMONEY is IFeeReceiver, ERC20, CoreOwnable, SystemStart {
    IERC20 public immutable asset;
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

    event Deposit(address indexed caller, address indexed owner, uint256 assets, uint256 shares);

    event Withdraw(
        address indexed caller,
        address indexed receiver,
        address indexed owner,
        uint256 assets,
        uint256 shares
    );

    mapping(address => AssetCooldown) public cooldowns;

    constructor(
        address _core,
        IERC20 _stable,
        address _feeAggregator,
        string memory _name,
        string memory _symbol
    ) ERC20(_name, _symbol) CoreOwnable(_core) SystemStart(_core) {
        asset = _stable;
        feeAggregator = _feeAggregator;
    }

    function deposit(uint256 assets, address receiver) public returns (uint256 shares) {
        // Check for rounding error since we round down in previewDeposit.
        require((shares = previewDeposit(assets)) != 0, "ZERO_SHARES");

        // Need to transfer before minting or ERC777s could reenter.
        asset.transferFrom(msg.sender, address(this), assets);

        _mint(receiver, shares);

        emit Deposit(msg.sender, receiver, assets, shares);
    }

    function mint(uint256 shares, address receiver) public returns (uint256 assets) {
        assets = previewMint(shares); // No need to check for rounding error, previewMint rounds up.

        // Need to transfer before minting or ERC777s could reenter.
        asset.transferFrom(msg.sender, address(this), assets);

        _mint(receiver, shares);

        emit Deposit(msg.sender, receiver, assets, shares);
    }

    function convertToShares(uint256 assets) public view returns (uint256) {
        uint256 supply = totalSupply(); // Saves an extra SLOAD if totalSupply is non-zero.

        return supply == 0 ? assets : Math.mulDiv(assets, supply, totalAssets(), Math.Rounding.Down);
    }

    function convertToAssets(uint256 shares) public view returns (uint256) {
        uint256 supply = totalSupply(); // Saves an extra SLOAD if totalSupply is non-zero.

        return supply == 0 ? shares : Math.mulDiv(shares, supply, totalAssets(), Math.Rounding.Down);
    }

    function previewDeposit(uint256 assets) public view returns (uint256) {
        return convertToShares(assets);
    }

    function previewMint(uint256 shares) public view returns (uint256) {
        uint256 supply = totalSupply(); // Saves an extra SLOAD if totalSupply is non-zero.

        return supply == 0 ? shares : Math.mulDiv(shares, supply, totalAssets(), Math.Rounding.Up);
    }

    function previewWithdraw(uint256 assets) public view returns (uint256) {
        uint256 supply = totalSupply(); // Saves an extra SLOAD if totalSupply is non-zero.

        return supply == 0 ? assets : Math.mulDiv(assets, supply, totalAssets(), Math.Rounding.Up);
    }

    function previewRedeem(uint256 shares) public view returns (uint256) {
        return convertToAssets(shares);
    }

    function maxDeposit(address) public view returns (uint256) {
        return type(uint256).max;
    }

    function maxMint(address) public view returns (uint256) {
        return type(uint256).max;
    }

    function maxWithdraw(address owner) public view returns (uint256) {
        return convertToAssets(balanceOf(owner));
    }

    function maxRedeem(address owner) public view returns (uint256) {
        return balanceOf(owner);
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
    function totalAssets() public view returns (uint256) {
        uint256 updateUntil = Math.min(periodFinish, block.timestamp);
        uint256 duration = updateUntil - lastUpdate;
        return storedTotalAssets + (duration * rewardsPerSecond);
    }

    // Update storedTotalAssets on withdraw/redeem
    // function beforeWithdraw(uint256 amount, uint256 shares) internal virtual override {
    //     super.beforeWithdraw(amount, shares);
    //     _updateDailyStream();
    //     storedTotalAssets -= amount;
    // }

    // // Update storedTotalAssets on deposit/mint
    // function afterDeposit(uint256 amount, uint256 shares) internal virtual override {
    //     storedTotalAssets += amount;
    //     _updateDailyStream();
    //     super.afterDeposit(amount, shares);
    // }

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
        updateUntil = Math.min(periodFinish, block.timestamp);
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
}
