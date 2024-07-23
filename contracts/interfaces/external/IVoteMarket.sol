// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IVoteMarket {
    function createBounty(
        address gauge,
        address manager,
        address rewardToken,
        uint8 numberOfPeriods,
        uint256 maxRewardPerVote,
        uint256 totalRewardAmount,
        address[] calldata blacklist,
        bool upgradeable
    ) external returns (uint256 newBountyId);

    function increaseBountyDuration(
        uint256 _bountyId,
        uint8 _additionnalPeriods,
        uint256 _increasedAmount,
        uint256 _newMaxPricePerVote
    ) external;

    function getPeriodsLeft(uint256 bountyId) external view returns (uint256 periodsLeft);
}
