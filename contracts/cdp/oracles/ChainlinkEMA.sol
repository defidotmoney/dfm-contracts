// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IChainlinkAggregator } from "../../interfaces/IChainlinkAggregator.sol";
import { IPriceOracle } from "../../interfaces/IPriceOracle.sol";

/**
    @title Chainlink EMA Oracle
    @author defidotmoney
    @dev Calculated an exponential moving average from a Chainlink Feed
 */
contract ChainlinkEMA is IPriceOracle {
    IChainlinkAggregator public immutable chainlinkFeed;

    uint256 public immutable OBSERVATIONS;
    uint256 public immutable FREQUENCY;

    uint256 private immutable LOOKBACK;
    uint256 private immutable SMOOTHING_FACTOR;

    uint256 public storedObservationTimestamp;
    ChainlinkResponse public storedResponse;
    uint256 public storedPrice;

    struct ChainlinkResponse {
        uint80 roundId;
        int256 answer;
        uint256 updatedAt;
    }

    constructor(IChainlinkAggregator _chainlink, uint256 _observations, uint256 _frequency) {
        chainlinkFeed = _chainlink;
        OBSERVATIONS = _observations;
        FREQUENCY = _frequency;
        LOOKBACK = _observations * 2;
        SMOOTHING_FACTOR = 2e18 / (_observations + 1);
    }

    function _getLatestRoundData() internal view returns (ChainlinkResponse memory response) {
        (response.roundId, response.answer, , response.updatedAt, ) = chainlinkFeed.latestRoundData();
        return response;
    }

    function _getRoundData(uint80 roundId) internal view returns (ChainlinkResponse memory response) {
        (response.roundId, response.answer, , response.updatedAt, ) = chainlinkFeed.getRoundData(roundId);
        return response;
    }

    /**
        @notice Returns the current oracle price, normalized to 1e18 precision
        @dev Called by all state-changing market / amm operations with the exception
             of `MainController.close_loan`
     */
    function price_w() external returns (uint256) {}

    /**
        @notice Returns the current oracle price, normalized to 1e18 precision
        @dev Read-only version used within view methods. Should always return
             the same value as `price_w`
     */
    function price() external view returns (uint256) {}
}
