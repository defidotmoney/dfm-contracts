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
        uint16 pctInBps;
        uint256 maximumAmount;
    }

    constructor(address _core, IERC20 _stable) CoreOwnable(_core) SystemStart(_core) {
        stableCoin = _stable;
    }

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
}
