// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { EnumerableSet } from "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
import { IVoteMarket } from "../interfaces/external/IVoteMarket.sol";
import { IFeeReceiver } from "../interfaces/IFeeReceiver.sol";
import { TokenRecovery } from "./dependencies/TokenRecovery.sol";

contract ReceiverVoteMarket is TokenRecovery, IFeeReceiver {
    using EnumerableSet for EnumerableSet.AddressSet;

    uint256 constant MIN_AMOUNT = 100 * 1e18;
    uint8 constant BOUNTY_PERIODS = 4;
    uint256 constant MAX_PRICE_PER_VOTE = type(uint256).max;

    address public immutable feeAggregator;
    IERC20 public immutable stableCoin;
    IVoteMarket public immutable voteMarket;

    EnumerableSet.AddressSet private __gauges;
    EnumerableSet.AddressSet private __blacklist;

    uint256 public totalAllocationPoints;

    mapping(address gauge => uint256 allocPoints) public gaugeAllocationPoints;
    mapping(address gauge => uint256 id) private bountyIds;

    struct GaugeAlloc {
        address gauge;
        uint256 points;
    }

    event BountyCreated(address indexed gauge, uint256 bountyId);
    event BountyRewardAdded(address indexed gauge, uint256 indexed bountyId, uint256 rewardAmount);

    event BlacklistSet(address account, bool isBlacklisted);
    event GaugeAllocationSet(address gauge, uint256 allocPoints);

    constructor(
        address core,
        IERC20 _stable,
        address _feeAggregator,
        IVoteMarket _voteMarket,
        GaugeAlloc[] memory _gauges,
        address[] memory _blacklist
    ) TokenRecovery(core) {
        feeAggregator = _feeAggregator;
        stableCoin = _stable;
        voteMarket = _voteMarket;

        _setGauges(_gauges);
        _setBlacklist(_blacklist, true);

        _stable.approve(address(_voteMarket), type(uint256).max);
    }

    function getGaugeCount() external view returns (uint256) {
        return __gauges.length();
    }

    function isGaugeAdded(address gauge) external view returns (bool) {
        return __gauges.contains(gauge);
    }

    function getGaugeList() external view returns (address[] memory) {
        return __gauges.values();
    }

    function quoteNotifyNewFees(uint256) external view returns (uint256) {
        return 0;
    }

    function notifyNewFees(uint256) external payable {
        require(msg.sender == feeAggregator);

        uint256 count = __gauges.length();
        if (count == 0) return;

        uint256 total = stableCoin.balanceOf(address(this));
        uint256 totalAlloc = totalAllocationPoints;

        for (uint256 i = 0; i < count; i++) {
            address gauge = __gauges.at(i);
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
                    __blacklist.values(),
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

    function setGauges(GaugeAlloc[] calldata gauges) external onlyOwner {
        _setGauges(gauges);
    }

    function setBlacklist(address[] calldata accounts, bool isBlacklisted) external onlyOwner {
        _setBlacklist(accounts, isBlacklisted);
    }

    function _setGauges(GaugeAlloc[] memory gauges) internal {
        uint256 totalAlloc = totalAllocationPoints;
        uint256 length = gauges.length;

        for (uint i = 0; i < length; i++) {
            address gauge = gauges[i].gauge;
            uint256 points = gauges[i].points;
            if (points > 0) {
                if (!__gauges.add(gauge)) {
                    totalAlloc -= gaugeAllocationPoints[gauge];
                }
                totalAlloc += points;
            } else {
                require(__gauges.remove(gauge), "DFM: cannot remove unset gauge");
                totalAlloc -= gaugeAllocationPoints[gauge];
            }
            emit GaugeAllocationSet(gauge, points);
            gaugeAllocationPoints[gauge] = points;
        }
        totalAllocationPoints = totalAlloc;
    }

    function _setBlacklist(address[] memory accounts, bool isBlacklisted) internal {
        uint256 length = accounts.length;
        for (uint i = 0; i < length; i++) {
            if (isBlacklisted) require(__blacklist.add(accounts[i]), "DFM: Account already added");
            else require(__blacklist.remove(accounts[i]), "DFM: Account not on list");
            emit BlacklistSet(accounts[i], isBlacklisted);
        }
    }
}
