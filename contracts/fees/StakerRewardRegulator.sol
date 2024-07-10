// SPDX-License-Identifier: MIT

import { IStakerRewardRegulator } from "../interfaces/IStakerRewardRegulator.sol";
import { IPriceOracle } from "../interfaces/IPriceOracle.sol";
import { CoreOwnable } from "../base/dependencies/CoreOwnable.sol";

pragma solidity 0.8.25;

/**
    @title Staker Reward Regulator
    @author defidotmoney
    @notice Dynamically controls the yield rate for the stablecoin staker.
            Useful as a tool to help maintain the stablecoin peg.
 */
contract StakerRewardRegulator is IStakerRewardRegulator, CoreOwnable {
    uint256 public constant MAX_PCT = 10000;
    uint256 public constant MAX_PRICE_RANGE = 1e17;

    IPriceOracle immutable stablecoinOracle;

    uint64 public minPrice;
    uint64 public maxPrice;
    uint64 public minStakerPct;
    uint64 public maxStakerPct;

    event SetPriceBounds(uint256 minPrice, uint256 maxPrice);
    event SetStakerPctBounds(uint256 minStakerPct, uint256 maxStakcerPct);

    constructor(
        address _core,
        IPriceOracle _stableOracle,
        uint256 _minPrice,
        uint256 _maxPrice,
        uint256 _minStakerPct,
        uint256 _maxStakerPct
    ) CoreOwnable(_core) {
        stablecoinOracle = _stableOracle;

        _setPriceBounds(_minPrice, _maxPrice);
        _setStakerPctBounds(_minStakerPct, _maxStakerPct);
    }

    /**
        @notice Get the stable amount given to `StableStaker` in the new reward period.
        @dev Called once per day from `StableStaker`.
        @param amount The available reward amount for the new period.
        @return stakerAmount Reward amount for the stable staker.
     */
    function getStakerRewardAmount(uint256 amount) external returns (uint256 stakerAmount) {
        uint256 price = stablecoinOracle.price_w();
        uint256 stakerPct;
        if (price >= maxPrice) stakerPct = maxStakerPct;
        else if (price <= minPrice) stakerPct = minStakerPct;
        else {
            stakerPct = ((price - minPrice) * MAX_PCT) / (maxPrice - minPrice);
            stakerPct = minStakerPct + ((stakerPct * (maxStakerPct - minStakerPct)) / MAX_PCT);
        }
        return (amount * stakerPct) / MAX_PCT;
    }

    function setPriceBounds(uint256 _minPrice, uint256 _maxPrice) external onlyOwner {
        _setPriceBounds(_minPrice, _maxPrice);
    }

    function setStakerPctBounds(uint256 _minStakerPct, uint256 _maxStakerPct) external onlyOwner {
        _setStakerPctBounds(_minStakerPct, _maxStakerPct);
    }

    function _setPriceBounds(uint256 _minPrice, uint256 _maxPrice) internal {
        require(_maxPrice >= 1e18, "DFM: maxPrice below 1e18");
        require(_minPrice <= 1e18, "DFM: minPrice above 1e18");
        require(_maxPrice >= _minPrice, "DFM: maxPrice > minPrice");
        require(_maxPrice - _minPrice <= MAX_PRICE_RANGE, "DFM: MAX_PRICE_RANGE");

        minPrice = uint64(_minPrice);
        maxPrice = uint64(_maxPrice);

        emit SetPriceBounds(_minPrice, _maxPrice);
    }

    function _setStakerPctBounds(uint256 _minStakerPct, uint256 _maxStakerPct) internal {
        require(_minStakerPct <= MAX_PCT, "DFM: minStakerPct > MAX_PCT");
        require(_maxStakerPct <= MAX_PCT, "DFM: maxStakerPct > MAX_PCT");
        require(_maxStakerPct >= _minStakerPct, "DFM: minStakerPct > maxStakerPct");

        minStakerPct = uint64(_minStakerPct);
        maxStakerPct = uint64(_maxStakerPct);

        emit SetStakerPctBounds(_minStakerPct, _maxStakerPct);
    }
}
