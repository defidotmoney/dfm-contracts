// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { EnumerableSet } from "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
import { TokenRecovery } from "./TokenRecovery.sol";

/**
    @title Gauge Allocation Fee Receiver Abstract Base
    @author defidotmoney
    @dev Shared logic for fee receivers distributing unevenly weighted incentives to Curve gauges
 */
abstract contract GaugeAllocReceiverBase is TokenRecovery {
    using EnumerableSet for EnumerableSet.AddressSet;

    uint256 public constant MIN_TOTAL_REWARD = 1000 * 1e18;
    uint256 public constant MAX_TOTAL_ALLOCATION_POINTS = 10000;

    IERC20 public immutable stableCoin;

    EnumerableSet.AddressSet private __gauges;
    EnumerableSet.AddressSet private __exclusions;

    uint256 public totalAllocationPoints;

    mapping(address gauge => uint256 allocPoints) public gaugeAllocationPoints;

    struct GaugeAlloc {
        address gauge;
        uint256 points;
    }

    event ExclusionListSet(address account, bool isExcluded);
    event GaugeAllocationSet(address gauge, uint256 allocPoints);

    constructor(
        address core,
        address _stable,
        address _target,
        GaugeAlloc[] memory _gauges,
        address[] memory _excluded
    ) TokenRecovery(core) {
        stableCoin = IERC20(_stable);

        _setGauges(_gauges);
        _setExclusionList(_excluded, true);

        IERC20(_stable).approve(_target, type(uint256).max);
    }

    function getGaugeList() public view returns (address[] memory) {
        return __gauges.values();
    }

    function getExclusionList() public view returns (address[] memory) {
        return __exclusions.values();
    }

    function setGauges(GaugeAlloc[] calldata gauges) external onlyOwner {
        _setGauges(gauges);
    }

    function setExclusionList(address[] calldata accounts, bool isExcluded) external onlyOwner {
        _setExclusionList(accounts, isExcluded);
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
        require(totalAlloc <= MAX_TOTAL_ALLOCATION_POINTS, "DFM: MAX_TOTAL_ALLOCATION_POINTS");
        totalAllocationPoints = totalAlloc;
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
