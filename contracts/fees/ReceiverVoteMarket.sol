// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IVoteMarket } from "../interfaces/external/IVoteMarket.sol";
import { IFeeReceiver } from "../interfaces/IFeeReceiver.sol";
import { GaugeAllocReceiverBase } from "./dependencies/GaugeAllocReceiverBase.sol";

/**
    @notice StakeDao VoteMarket Receiver
    @author defidotmoney
    @dev Receives fees from `PrimaryFeeAggregator` and deposits into VoteMarket
         https://github.com/stake-dao/x-chain-vm/blob/23fe83a/src/Platform.sol
 */
contract VoteMarketFeeReceiver is IFeeReceiver, GaugeAllocReceiverBase {
    uint8 constant BOUNTY_PERIODS = 4;
    uint256 constant MAX_PRICE_PER_VOTE = type(uint256).max;

    address public immutable feeAggregator;
    IVoteMarket public immutable voteMarket;

    event BountyCreated(address indexed gauge, uint256 bountyId);
    event BountyRewardAdded(address indexed gauge, uint256 indexed bountyId, uint256 rewardAmount);

    mapping(address gauge => uint256 id) private bountyIds;

    constructor(
        address core,
        address _stable,
        address _feeAggregator,
        address _voteMarket,
        GaugeAlloc[] memory _gauges,
        address[] memory _excluded
    ) GaugeAllocReceiverBase(core, _stable, _voteMarket, _gauges, _excluded) {
        feeAggregator = _feeAggregator;
        voteMarket = IVoteMarket(_voteMarket);
    }

    function quoteNotifyNewFees(uint256) external view returns (uint256) {
        return 0;
    }

    function notifyNewFees(uint256) external payable {
        require(msg.sender == feeAggregator, "DFM: Only feeAggregator");

        address[] memory gauges = getGaugeList();
        uint256 length = gauges.length;
        if (length == 0) return;

        uint256 total = stableCoin.balanceOf(address(this));
        uint256 totalAlloc = totalAllocationPoints;

        for (uint256 i = 0; i < length; i++) {
            address gauge = gauges[i];
            uint256 amount = (total * gaugeAllocationPoints[gauge]) / totalAlloc;
            if (amount < MIN_AMOUNT) continue;

            uint256 bountyId = bountyIds[gauge];
            uint256 periodsLeft;
            if (bountyId > 0) {
                bountyId -= 1;
                periodsLeft = voteMarket.getPeriodsLeft(bountyId);
            }

            if (periodsLeft == 0) {
                bountyId = voteMarket.createBounty(
                    gauge,
                    address(this),
                    address(stableCoin),
                    BOUNTY_PERIODS,
                    MAX_PRICE_PER_VOTE,
                    amount,
                    getExclusionList(),
                    true
                );
                bountyIds[gauge] = bountyId + 1;
                emit BountyCreated(gauge, bountyId);
            } else {
                uint8 periodIncrease;
                if (periodsLeft < BOUNTY_PERIODS) periodIncrease = uint8(BOUNTY_PERIODS - periodsLeft);
                voteMarket.increaseBountyDuration(bountyId, periodIncrease, amount, MAX_PRICE_PER_VOTE);
            }

            emit BountyRewardAdded(gauge, bountyId, amount);
        }

        if (msg.value != 0) {
            (bool success, ) = msg.sender.call{ value: msg.value }("");
            require(success, "DFM: Gas refund transfer failed");
        }
    }
}
