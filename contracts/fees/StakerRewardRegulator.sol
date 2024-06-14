// SPDX-License-Identifier: MIT

import "../interfaces/IStakerRewardRegulator.sol";

pragma solidity 0.8.25;

/**
    @title Staker Reward Regulator
    @author defidotmoney
    @notice Dynamically controls the yield rate for the stablecoin staker.
            Useful as a tool to help maintain the stablecoin peg.
 */
contract StakerRewardRegulator is IStakerRewardRegulator {
    address immutable stableStaker;

    constructor(address _staker) {
        stableStaker = _staker;
    }

    /**
        @notice Get the stable amount given to `StableStaker` in the new reward period.
        @dev * Called once per day from `StableStaker`.
             * The return value must be less than or equal to the initial amount.
             * `amount - stakerAmount` is the amount sent onward to `GovStaker`.
        @param amount The available reward amount for the new peiord.
        @return stakerAmount Reward amount for the stable staker.
     */
    function getStakerRewardAmount(uint256 amount) external returns (uint256 stakerAmount) {
        require(msg.sender == stableStaker, "DFM: Only staker");
        // TODO
    }
}
