// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { EnumerableSet } from "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
import { IVoteMarket } from "../interfaces/external/IVoteMarket.sol";
import { LocalReceiverBase } from "./dependencies/LocalReceiverBase.sol";
import { GaugeAllocReceiverBase } from "./dependencies/GaugeAllocReceiverBase.sol";

/**
    @notice StakeDao VoteMarket Receiver
    @author defidotmoney
    @dev Receives fees from `PrimaryFeeAggregator` and deposits into VoteMarket
         https://github.com/stake-dao/x-chain-vm/blob/23fe83a/src/Platform.sol
 */
contract VoteMarketFeeReceiver is LocalReceiverBase, GaugeAllocReceiverBase {
    using EnumerableSet for EnumerableSet.AddressSet;

    uint8 constant BOUNTY_PERIODS = 4;
    uint256 constant MAX_PRICE_PER_VOTE = type(uint256).max;

    IVoteMarket public immutable voteMarket;

    EnumerableSet.AddressSet private __exclusions;

    event BountyCreated(address indexed gauge, uint256 bountyId);
    event BountyRewardAdded(address indexed gauge, uint256 indexed bountyId, uint256 rewardAmount);
    event ExclusionListSet(address account, bool isExcluded);

    mapping(address gauge => uint256 id) private bountyIds;

    constructor(
        address core,
        address _stable,
        address _feeAggregator,
        address _voteMarket,
        GaugeAlloc[] memory _gauges,
        address[] memory _excluded
    ) LocalReceiverBase(_feeAggregator) GaugeAllocReceiverBase(core, _stable, _voteMarket, _gauges) {
        voteMarket = IVoteMarket(_voteMarket);

        _setExclusionList(_excluded, true);
    }

    function getExclusionList() public view returns (address[] memory) {
        return __exclusions.values();
    }

    function _notifyNewFees(uint256) internal override returns (uint256) {
        uint256 total = stableCoin.balanceOf(address(this));
        address[] memory gauges = getGaugeList();
        uint256 length = gauges.length;
        if (length == 0 || total < MIN_TOTAL_REWARD) {
            return 0;
        }

        uint256 totalAlloc = totalAllocationPoints;

        for (uint256 i = 0; i < length; i++) {
            address gauge = gauges[i];
            uint256 amount = (total * gaugeAllocationPoints[gauge]) / totalAlloc;

            uint256 bountyId = bountyIds[gauge];
            uint256 periodsLeft;
            if (bountyId > 0) {
                bountyId -= 1;
                periodsLeft = voteMarket.getPeriodsLeft(bountyId);
            }

            if (periodsLeft == 0) {
                // bounty does not exist or has expired, create a new one
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
                // +1 to bountyId so we can trust that zero == not created
                bountyIds[gauge] = bountyId + 1;
                emit BountyCreated(gauge, bountyId);
            } else {
                // bounty exists and is still active, add rewards and increase the duration
                uint8 periodIncrease;
                if (periodsLeft < BOUNTY_PERIODS) periodIncrease = uint8(BOUNTY_PERIODS - periodsLeft);
                voteMarket.increaseBountyDuration(bountyId, periodIncrease, amount, MAX_PRICE_PER_VOTE);
            }

            emit BountyRewardAdded(gauge, bountyId, amount);
        }

        return total;
    }

    /**
        @notice Add or remove addresses from the exclusion list
        @dev Excluded addresses are not eligible for any bounties created by
             this contract. Adding or removing an address only affects future
             bounties, it does not modify the blacklists of existing bounties.
     */
    function setExclusionList(address[] calldata accounts, bool isExcluded) external onlyOwner {
        _setExclusionList(accounts, isExcluded);
    }

    function _setExclusionList(address[] memory accounts, bool isExcluded) internal {
        uint256 length = accounts.length;
        for (uint i = 0; i < length; i++) {
            if (isExcluded) require(__exclusions.add(accounts[i]), "DFM: Account already added");
            else require(__exclusions.remove(accounts[i]), "DFM: Account not on list");
            emit ExclusionListSet(accounts[i], isExcluded);
        }
    }
}
