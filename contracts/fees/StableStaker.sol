// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";
import "../base/dependencies/CoreOwnable.sol";
import "../base/dependencies/SystemStart.sol";
import "../interfaces/IFeeReceiver.sol";
import "../interfaces/IStakerRewardRegulator.sol";

/**
    @title  StableStaker: ERC4626-ish Staking Contract
    @author defidotmoney, with inspiration from:
             * ERC4626 Alliance: xERC4626
             * Ethena Labs: StakedUSDeV2
             * Zefram: xERC20
    @notice Allows users to stake stablecoins to earn a portion of protocol yield.
    @dev This contract mostly follows the ERC4626 standard, however it breaks
         compatibility by lacking `withdraw` and `redeem` functions. Withdrawals
         are possible by calling `cooldownAssets` or `cooldownShares`, waiting
         for the `cooldownDuration` to pass, and then calling `unstake`.
 */
contract StableStaker is IFeeReceiver, ERC20, CoreOwnable, SystemStart {
    uint256 public constant maxDeposit = type(uint256).max;
    uint256 public constant maxMint = type(uint256).max;
    uint256 public constant MAX_COOLDOWN_DURATION = 4 weeks;

    IERC20 public immutable asset;
    address public feeAggregator;
    IStakerRewardRegulator public rewardRegulator;
    address public govStaker;

    uint32 public cooldownDuration;

    uint16 public lastDistributionWeek;
    uint32 public lastDistributionDay;

    uint32 public lastUpdate;
    uint32 public periodFinish;

    uint256 public rewardsPerSecond;

    /// @notice The amount of `asset` received in the current active reward week
    uint256 public lastWeeeklyAmountReceived;

    uint256 public storedTotalAssets;
    uint256 public totalCooldownAssets;

    mapping(address => AssetCooldown) public cooldowns;

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

    constructor(
        address _core,
        IERC20 _stable,
        address _feeAggregator,
        string memory _name,
        string memory _symbol,
        uint32 _cooldownDuration
    ) ERC20(_name, _symbol) CoreOwnable(_core) SystemStart(_core) {
        asset = _stable;
        feeAggregator = _feeAggregator;
        cooldownDuration = _cooldownDuration;
    }

    /**
        @notice Compute the amount of tokens available to share holders.
        @dev Increases linearly during an active reward distribution period.
     */
    function totalAssets() public view returns (uint256) {
        uint256 updateUntil = Math.min(periodFinish, block.timestamp);
        uint256 duration = updateUntil - lastUpdate;
        return storedTotalAssets + (duration * rewardsPerSecond);
    }

    function convertToShares(uint256 assets) public view returns (uint256) {
        uint256 supply = totalSupply();

        return supply == 0 ? assets : Math.mulDiv(assets, supply, totalAssets(), Math.Rounding.Down);
    }

    function convertToAssets(uint256 shares) public view returns (uint256) {
        uint256 supply = totalSupply();

        return supply == 0 ? shares : Math.mulDiv(shares, supply, totalAssets(), Math.Rounding.Down);
    }

    function previewDeposit(uint256 assets) public view returns (uint256) {
        return convertToShares(assets);
    }

    function previewMint(uint256 shares) public view returns (uint256) {
        uint256 supply = totalSupply();

        return supply == 0 ? shares : Math.mulDiv(shares, supply, totalAssets(), Math.Rounding.Up);
    }

    function previewWithdraw(uint256 assets) public view returns (uint256) {
        uint256 supply = totalSupply();

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

    function deposit(uint256 assets, address receiver) external returns (uint256 shares) {
        // Check for rounding error since we round down in previewDeposit.
        require((shares = previewDeposit(assets)) != 0, "ZERO_SHARES");
        _updateDailyStream();
        _deposit(assets, shares, receiver);
        return shares;
    }

    function mint(uint256 shares, address receiver) external returns (uint256 assets) {
        _updateDailyStream();

        assets = previewMint(shares);
        _deposit(assets, shares, receiver);
        return assets;
    }

    /**
        @notice Redeem assets and start a cooldown to claim the underlying asset.
        @param assets Amount of assets to redeem.
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

        // TODO event
    }

    function notifyWeeklyFees(uint256) external {
        require(msg.sender == feeAggregator);

        uint256 updateUntil = _advanceCurrentStream();
        uint256 residualAmount = (periodFinish - updateUntil) * rewardsPerSecond;
        uint256 newAmount = asset.balanceOf(address(this)) - storedTotalAssets - totalCooldownAssets - residualAmount;
        lastWeeeklyAmountReceived = newAmount;
        _setNewStream(newAmount, residualAmount);
    }

    function setCooldownDuration(uint32 _cooldownDuration) external onlyOwner {
        require(_cooldownDuration <= MAX_COOLDOWN_DURATION, "sMONEY: Invalid duration");
        cooldownDuration = _cooldownDuration;
    }

    function setFeeAggregator(address _feeAggregator) external onlyOwner {
        feeAggregator = _feeAggregator;
    }

    function setRewardRegulator(IStakerRewardRegulator _regulator) external onlyOwner {
        rewardRegulator = _regulator;
    }

    function setGovStaker(address _govStaker) external onlyOwner {
        govStaker = _govStaker;
    }

    /** @dev Shared logic for `deposit` and `mint` */
    function _deposit(uint256 assets, uint256 shares, address receiver) internal {
        asset.transferFrom(msg.sender, address(this), assets);

        _mint(receiver, shares);
        storedTotalAssets += assets;

        emit Deposit(msg.sender, receiver, assets, shares);
    }

    /** @dev Shared logic for `cooldownAssets` and `cooldownShares` */
    function _cooldown(uint256 assets, uint256 shares) internal {
        require(assets > 0, "sMONEY: zero assets");

        cooldowns[msg.sender].cooldownEnd = uint32(block.timestamp + cooldownDuration);
        cooldowns[msg.sender].underlyingAmount = uint224(cooldowns[msg.sender].underlyingAmount + assets);
        totalCooldownAssets = totalCooldownAssets + assets;
        storedTotalAssets = storedTotalAssets - assets;

        _burn(msg.sender, shares);

        // TODO event
    }

    /**
        @dev Advance the current reward stream, and optionally update the stream
             within the current week. If a new week has started, the stream can
             only be updated through a call to `notifyWeeklyFees`.
    */
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

    /** @dev Advance the current reward stream */
    function _advanceCurrentStream() internal returns (uint256 updateUntil) {
        updateUntil = Math.min(periodFinish, block.timestamp);
        uint256 duration = updateUntil - lastUpdate;
        if (duration > 0) {
            storedTotalAssets = storedTotalAssets + (duration * rewardsPerSecond);
            lastUpdate = uint32(updateUntil);
        }
        return updateUntil;
    }

    /** @dev Start a new reward stream period */
    function _setNewStream(uint256 newAmount, uint256 residualAmount) internal {
        uint256 stakerAmount = rewardRegulator.getStakerRewardAmount(newAmount);
        require(stakerAmount <= newAmount, "sMONEY: Invalid stakerAmount");

        uint256 govAmount = newAmount - stakerAmount;
        if (govAmount > 0) {
            asset.transfer(govStaker, govAmount);
            // TODO notify?
        }

        stakerAmount += residualAmount;
        rewardsPerSecond = stakerAmount / 2 days;

        lastUpdate = uint32(block.timestamp);
        periodFinish = uint32(block.timestamp + 2 days);
        lastDistributionDay = uint32(getDay());
    }
}
