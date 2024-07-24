// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IVotium } from "../interfaces/external/IVotium.sol";
import { IFeeReceiverLzCompose } from "../interfaces/IFeeReceiverLzCompose.sol";
import { GaugeAllocReceiverBase } from "./dependencies/GaugeAllocReceiverBase.sol";

/**
    @notice Votium Fee Receiver
    @author defidotmoney
    @dev Receives fees bridged from `LzComposeForwarder` and deposits into Votium
         https://github.com/oo-00/Votium/blob/80eb7fd/contracts/Votium.sol
 */
contract VotiumFeeReceiver is IFeeReceiverLzCompose, GaugeAllocReceiverBase {
    IVotium public immutable votium;
    address public immutable endpoint;

    constructor(
        address core,
        address _stable,
        address _votium,
        address _endpoint,
        GaugeAlloc[] memory _gauges,
        address[] memory _excluded
    ) GaugeAllocReceiverBase(core, _stable, _votium, _gauges, _excluded) {
        votium = IVotium(_votium);
        endpoint = _endpoint;
    }

    function lzCompose(address _from, bytes32, bytes calldata, address, bytes calldata) external payable {
        require(msg.sender == endpoint, "DFM: Only lzEndpoint");
        require(_from == address(stableCoin), "DFM: Incorrect oApp");
        require(msg.value == 0, "DFM: msg.value > 0");

        address[] memory gauges = getGaugeList();
        uint256 length = gauges.length;
        if (length == 0) return;

        uint256 total = stableCoin.balanceOf(address(this));
        if (total < MIN_TOTAL_REWARD) return;

        uint256 totalAlloc = totalAllocationPoints;

        uint256[] memory amounts = new uint256[](length);
        for (uint256 i = 0; i < length; i++) {
            amounts[i] = (total * gaugeAllocationPoints[gauges[i]]) / totalAlloc;
        }

        uint256 round = votium.activeRound();
        votium.depositUnevenSplitGauges(address(stableCoin), round, gauges, amounts, 0, getExclusionList());
    }
}
