// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { EnumerableSet } from "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
import { TokenRecovery } from "./dependencies/TokenRecovery.sol";
import { IVotium } from "../interfaces/external/IVotium.sol";
import { IFeeReceiverLzCompose } from "../interfaces/IFeeReceiverLzCompose.sol";

contract VotiumFeeReceiver is TokenRecovery, IFeeReceiverLzCompose {
    using EnumerableSet for EnumerableSet.AddressSet;

    uint256 constant MIN_AMOUNT = 100 * 1e18;

    IERC20 public immutable stableCoin;
    IVotium public immutable votium;
    address public immutable endpoint;

    EnumerableSet.AddressSet private __gauges;

    constructor(address core, IERC20 _stable, IVotium _votium, address _endpoint) TokenRecovery(core) {
        stableCoin = _stable;
        votium = _votium;
        endpoint = _endpoint;

        _stable.approve(address(_votium), type(uint256).max);
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

    function lzCompose(address _from, bytes32, bytes calldata, address, bytes calldata) external payable {
        require(msg.sender == endpoint, "DFM: Only lzEndpoint");
        require(_from == address(stableCoin), "DFM: Incorrect oApp");
        require(msg.value == 0, "DFM: msg.value > 0");

        uint256 count = __gauges.length();
        if (count == 0) return;

        uint256 amount = stableCoin.balanceOf(address(this)) / count;
        if (amount < MIN_AMOUNT) return;

        uint256 round = votium.activeRound();
        votium.depositSplitGauges(address(stableCoin), amount, round, __gauges.values(), 0, new address[](0));
    }

    function addGauges(address[] calldata gauges) external onlyOwner {
        uint256 length = gauges.length;
        for (uint i = 0; i < length; i++) {
            require(__gauges.add(gauges[i]), "DFM: Gauge already added");
        }
    }

    function removeGauges(address[] calldata gauges) external onlyOwner {
        uint256 length = gauges.length;
        for (uint i = 0; i < length; i++) {
            require(__gauges.remove(gauges[i]), "DFM: Unknown gauge");
        }
    }

    // TODO
    // exclusion list
    // gauge weighting
}
