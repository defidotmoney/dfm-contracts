// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IStakerRewardRegulator {
    /**
        @notice Get the stable amount given to `StableStaker` in the new reward period.
        @dev * Called once per day from `StableStaker`.
             * The return value must be less than or equal to the initial amount.
             * `amount - stakerAmount` is the amount sent onward to `GovStaker`.
        @param amount The available reward amount for the new period.
        @return stakerAmount Reward amount for the stable staker.
     */
    function getStakerRewardAmount(uint256 amount) external returns (uint256 stakerAmount);
}
