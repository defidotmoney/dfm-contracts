// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "../base/dependencies/CoreOwnable.sol";
import "../base/dependencies/SystemStart.sol";
import "../interfaces/IFeeReceiver.sol";

/**
    @title Primary Chain Fee Aggregator
    @author defidotmoney
    @notice Receives stablecoin fees from all chains and coordinates onward
            distribution throughout the system
 */
contract PrimaryFeeAggregator is CoreOwnable, SystemStart {
    uint256 internal constant MAX_BPS = 10000;
    IERC20 public immutable stableCoin;

    IFeeReceiver public fallbackReceiver;
    uint16 public lastDistributionWeek;
    uint16 public totalPriorityReceiverPct;

    PriorityReceiver[] public priorityReceivers;

    struct PriorityReceiver {
        IFeeReceiver target;
        uint16 pctInBps; // Percent of weekly fees sent to this receiver.
        uint256 maximumAmount; // Maximum amount sent each week. Set to 0 for no limit.
    }

    constructor(address _core, IERC20 _stable) CoreOwnable(_core) SystemStart(_core) {
        stableCoin = _stable;
    }

    function priorityReceiverCount() external view returns (uint256) {
        return priorityReceivers.length;
    }

    // --- unguarded external functions

    function processWeeklyDistribution() external {
        require(lastDistributionWeek < getWeek(), "DFM: Already distro'd this week");
        lastDistributionWeek = uint16(getWeek());

        uint256 initialAmount = stableCoin.balanceOf(address(this));
        require(initialAmount > 0, "DFM: Nothing to distribute");

        uint256 length = priorityReceivers.length;
        for (uint256 i = 0; i < length; i++) {
            PriorityReceiver memory p = priorityReceivers[i];
            uint256 amount = (initialAmount * p.pctInBps) / MAX_BPS;
            if (p.maximumAmount != 0 && amount > p.maximumAmount) amount = p.maximumAmount;
            stableCoin.transfer(address(p.target), amount);
            p.target.notifyWeeklyFees(amount);
        }

        // we fetch the balance again so that priority receivers have
        // the option to return a portion of their received balance
        uint256 amount = stableCoin.balanceOf(address(this));
        if (amount > 0) {
            stableCoin.transfer(address(fallbackReceiver), amount);
            fallbackReceiver.notifyWeeklyFees(amount);
        }
    }

    // --- owner-only external functions ---

    /**
        @notice Add new priority receivers
        @param _receivers Array of new receivers to add
     */
    function addPriorityReceivers(PriorityReceiver[] calldata _receivers) external onlyOwner {
        uint256 totalPct = totalPriorityReceiverPct;

        uint256 length = _receivers.length;
        for (uint256 i = 0; i < length; i++) {
            totalPct += _receivers[i].pctInBps;
            priorityReceivers.push(_receivers[i]);
        }
        require(totalPct <= MAX_BPS, "DFM: priority receiver pct > 100");
        totalPriorityReceiverPct = uint16(totalPct);
    }

    /**
        @notice Remove a priority receiver
        @param idx Index of the receiver to remove from `priorityReceivers`
     */
    function removePriorityReceiver(uint256 idx) external onlyOwner {
        uint256 maxIdx = priorityReceivers.length - 1;
        totalPriorityReceiverPct -= priorityReceivers[idx].pctInBps;
        if (idx < maxIdx) {
            priorityReceivers[idx] = priorityReceivers[maxIdx];
        }
        priorityReceivers.pop();
    }

    /**
        @notice Set the fallback receiver
        @dev The fallback receiver is sent the remaining stablecoin balance
             each week, after all the priority receivers have been funded.
        @param _fallbackReceiver Fallback receiver address.
     */
    function setFallbackReceiver(IFeeReceiver _fallbackReceiver) external onlyOwner {
        fallbackReceiver = _fallbackReceiver;
    }
}
