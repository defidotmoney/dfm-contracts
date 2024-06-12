// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "../base/dependencies/CoreOwnable.sol";
import "../base/dependencies/SystemStart.sol";

/**
    @title Primary Chain Fee Aggregator
    @author defidotmoney
    @notice Receives stablecoin fees from all chains and coordinates onward
            distribution throughout the system
 */
contract PrimaryFeeAggregator is CoreOwnable, SystemStart {
    IERC20 public immutable stableCoin;

    address public fallbackReceiver;

    uint16 public lastDistributionEpoch;
    uint16 public totalPriorityReceiverPct;

    PriorityReceiver[] public priorityReceivers;

    struct PriorityReceiver {
        address target;
        uint16 pctInBps;
        uint256 maximumAmount;
    }

    constructor(address _core, IERC20 _stable) CoreOwnable(_core) SystemStart(_core) {
        stableCoin = _stable;
    }
}
