// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { TokenRecovery } from "./dependencies/TokenRecovery.sol";
import { SystemStart } from "../base/dependencies/SystemStart.sol";
import { IFeeReceiver } from "../interfaces/IFeeReceiver.sol";

/**
    @title Primary Chain Fee Aggregator
    @author defidotmoney
    @notice Receives stablecoin fees from all chains and coordinates onward
            distribution throughout the system
 */
contract PrimaryFeeAggregator is TokenRecovery, SystemStart {
    uint256 internal constant MAX_BPS = 10000;
    IERC20 public immutable stableCoin;

    IFeeReceiver public fallbackReceiver;
    uint16 public lastDistributionWeek;
    uint16 public totalPriorityReceiverPct;
    uint256 public callerIncentive;

    PriorityReceiver[] public priorityReceivers;

    struct PriorityReceiver {
        IFeeReceiver target;
        uint16 pctInBps; // Percent of weekly fees sent to this receiver.
        uint256 maximumAmount; // Maximum amount sent each week. Set to 0 for no limit.
    }

    event ProcessWeeklyDistribution(address indexed caller, uint256 distroAmount, uint256 callerIncentive);
    event AddPriorityReceiver(IFeeReceiver receiver, uint256 pctInBps, uint256 maxAmount);
    event RemovePriorityReceiver(IFeeReceiver receiver);
    event SetFallbackReceiver(IFeeReceiver receiver);
    event SetCallerIncentive(uint256 amount);

    constructor(address _core, IERC20 _stable, uint256 _callerIncentive) TokenRecovery(_core) SystemStart(_core) {
        stableCoin = _stable;
        callerIncentive = _callerIncentive;
    }

    receive() external payable {}

    function priorityReceiverCount() external view returns (uint256) {
        return priorityReceivers.length;
    }

    function quoteProcessWeeklyDistribution() external view returns (uint256 nativeFee) {
        if (lastDistributionWeek == getWeek()) return 0;

        uint256 initialAmount = stableCoin.balanceOf(address(this));
        uint256 amount = callerIncentive;
        if (initialAmount <= amount * 2) return 0;
        initialAmount -= amount;
        uint256 remaining = initialAmount;

        uint256 length = priorityReceivers.length;
        for (uint256 i = 0; i < length; i++) {
            PriorityReceiver memory p = priorityReceivers[i];
            amount = (initialAmount * p.pctInBps) / MAX_BPS;
            if (p.maximumAmount != 0 && amount > p.maximumAmount) amount = p.maximumAmount;
            nativeFee += p.target.quoteNotifyNewFees(amount);
            remaining -= amount;
        }

        if (remaining > 0) {
            nativeFee += fallbackReceiver.quoteNotifyNewFees(remaining);
        }
    }

    // --- unguarded external functions ---

    function processWeeklyDistribution() external payable {
        require(lastDistributionWeek < getWeek(), "DFM: Already distro'd this week");
        lastDistributionWeek = uint16(getWeek());

        uint256 initialAmount = stableCoin.balanceOf(address(this));
        uint256 callerIncentive_ = callerIncentive;
        require(initialAmount > callerIncentive_ * 2, "DFM: Nothing to distribute");

        // transfer incentive to the caller
        if (callerIncentive_ > 0) {
            stableCoin.transfer(msg.sender, callerIncentive_);
            initialAmount -= callerIncentive_;
        }

        uint256 length = priorityReceivers.length;
        for (uint256 i = 0; i < length; i++) {
            PriorityReceiver memory p = priorityReceivers[i];
            uint256 amount = (initialAmount * p.pctInBps) / MAX_BPS;
            if (p.maximumAmount != 0 && amount > p.maximumAmount) amount = p.maximumAmount;
            stableCoin.transfer(address(p.target), amount);
            p.target.notifyNewFees{ value: address(this).balance }(amount);
        }

        // we fetch the balance again so that priority receivers have
        // the option to return a portion of their received balance
        uint256 amount = stableCoin.balanceOf(address(this));
        if (amount > 0) {
            stableCoin.transfer(address(fallbackReceiver), amount);
            fallbackReceiver.notifyNewFees{ value: address(this).balance }(amount);
        }

        if (address(this).balance > 0) {
            (bool success, ) = msg.sender.call{ value: address(this).balance }("");
            require(success, "DFM: Gas refund transfer failed");
        }

        emit ProcessWeeklyDistribution(msg.sender, initialAmount, callerIncentive_);
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
            emit AddPriorityReceiver(_receivers[i].target, _receivers[i].pctInBps, _receivers[i].maximumAmount);
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
        IFeeReceiver receiver;

        if (idx < maxIdx) {
            receiver = priorityReceivers[idx].target;
            priorityReceivers[idx] = priorityReceivers[maxIdx];
        } else {
            receiver = priorityReceivers[maxIdx].target;
        }

        priorityReceivers.pop();

        emit RemovePriorityReceiver(receiver);
    }

    /**
        @notice Set the fallback receiver
        @dev The fallback receiver is sent the remaining stablecoin balance
             each week, after all the priority receivers have been funded.
        @param _fallbackReceiver Fallback receiver address.
     */
    function setFallbackReceiver(IFeeReceiver _fallbackReceiver) external onlyOwner {
        fallbackReceiver = _fallbackReceiver;
        emit SetFallbackReceiver(_fallbackReceiver);
    }

    /**
        @notice Set the caller incentive
        @dev This amount is paid to the caller of `processWeeklyDistribution`
             as an incentive to keep the fee distribution system functioning
        @param _callerIncentive Amount paid as an incentive.
     */
    function setCallerIncentive(uint256 _callerIncentive) external onlyOwner {
        callerIncentive = _callerIncentive;
        emit SetCallerIncentive(_callerIncentive);
    }
}
