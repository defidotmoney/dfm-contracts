// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IVotium } from "../interfaces/external/IVotium.sol";
import { GaugeAllocReceiverBase } from "./dependencies/GaugeAllocReceiverBase.sol";
import { LzComposeReceiverBase } from "./dependencies/LzComposeReceiverBase.sol";

/**
    @notice Votium Fee Receiver
    @author defidotmoney
    @dev Receives fees bridged from `LzComposeForwarder` and deposits into Votium
         https://github.com/oo-00/Votium/blob/80eb7fd/contracts/Votium.sol
 */
contract VotiumFeeReceiver is LzComposeReceiverBase, GaugeAllocReceiverBase {
    IVotium public immutable votium;

    event IncentivesAdded(address[] gauges, uint256[] amounts);

    constructor(
        address core,
        address _stable,
        address _votium,
        address _endpoint,
        address _remoteCaller,
        GaugeAlloc[] memory _gauges
    )
        LzComposeReceiverBase(_endpoint, _stable, _remoteCaller, false)
        GaugeAllocReceiverBase(core, _stable, _votium, _gauges)
    {
        votium = IVotium(_votium);
    }

    function _notifyNewFees(uint256) internal override returns (uint256) {
        address[] memory gauges = getGaugeList();
        uint256 length = gauges.length;
        if (length == 0) return 0;

        uint256 total = stableCoin.balanceOf(address(this));
        if (total < MIN_TOTAL_REWARD) return 0;

        uint256 totalAlloc = totalAllocationPoints;

        uint256[] memory amounts = new uint256[](length);
        for (uint256 i = 0; i < length; i++) {
            amounts[i] = (total * gaugeAllocationPoints[gauges[i]]) / totalAlloc;
        }

        votium.depositUnevenSplitGaugesSimple(address(stableCoin), gauges, amounts);
        emit IncentivesAdded(gauges, amounts);
        return total;
    }

    /**
        @dev Retrieve unprocessed incentives in case a gauge has been killed
     */
    function withdrawUnprocessed(uint256 _round, address _gauge, uint256 _incentive) external onlyOwner {
        votium.withdrawUnprocessed(_round, _gauge, _incentive);
    }
}
