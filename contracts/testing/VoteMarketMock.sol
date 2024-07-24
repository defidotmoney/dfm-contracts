// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { IVoteMarket } from "../interfaces/external/IVoteMarket.sol";

contract VoteMarketMock is IVoteMarket {
    IERC20 public immutable stableCoin;

    uint256 public nextBountyId;

    mapping(uint256 bountyId => uint256 lastPeriod) lastPeriod;

    event MockNewBounty(
        uint256 bountyId,
        address gauge,
        uint256 numberOfPeriods,
        uint256 maxRewardPerVote,
        uint256 totalRewardAmount,
        address[] blacklist
    );

    constructor(IERC20 _stable) {
        stableCoin = _stable;
    }

    function getPeriod() public view returns (uint256) {
        return block.timestamp / 604800;
    }

    function getPeriodsLeft(uint256 bountyId) public view returns (uint256 periodsLeft) {
        if (lastPeriod[bountyId] > getPeriod()) return lastPeriod[bountyId] - getPeriod();
        else return 0;
    }

    function createBounty(
        address gauge,
        address manager,
        address rewardToken,
        uint8 numberOfPeriods,
        uint256 maxRewardPerVote,
        uint256 totalRewardAmount,
        address[] calldata blacklist,
        bool upgradeable
    ) external returns (uint256 newBountyId) {
        require(gauge != address(0));
        require(manager == msg.sender);
        require(rewardToken == address(stableCoin));
        require(numberOfPeriods >= 2);
        require(maxRewardPerVote > 0);
        require(totalRewardAmount > 0);
        require(upgradeable);

        stableCoin.transferFrom(msg.sender, address(this), totalRewardAmount);
        uint256 bountyId = nextBountyId;
        nextBountyId += 1;
        lastPeriod[bountyId] = getPeriod() + numberOfPeriods + 1;

        emit MockNewBounty(bountyId, gauge, numberOfPeriods, maxRewardPerVote, totalRewardAmount, blacklist);

        return bountyId;
    }

    function increaseBountyDuration(
        uint256 _bountyId,
        uint8 _additionnalPeriods,
        uint256 _increasedAmount,
        uint256 _newMaxPricePerVote
    ) external {
        require(getPeriodsLeft(_bountyId) > 0);
        require(_increasedAmount > 0);
        require(_newMaxPricePerVote > 0);
        lastPeriod[_bountyId] += _additionnalPeriods;

        stableCoin.transferFrom(msg.sender, address(this), _increasedAmount);
    }
}
