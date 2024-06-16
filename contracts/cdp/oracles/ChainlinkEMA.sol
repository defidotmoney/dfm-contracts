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

        (storedPrice, storedResponse) = _getEmaWithoutPreviousData();
        storedObservationTimestamp = _getCurrentObservationTimestamp();
    }

    function _getCurrentObservationTimestamp() internal view returns (uint256) {
        return (block.timestamp / FREQUENCY) * FREQUENCY;
    }

    function _getLatestRoundData() internal view returns (ChainlinkResponse memory response) {
        (response.roundId, response.answer, , response.updatedAt, ) = chainlinkFeed.latestRoundData();
        return response;
    }

    function _getRoundData(uint80 roundId) internal view returns (ChainlinkResponse memory response) {
        (response.roundId, response.answer, , response.updatedAt, ) = chainlinkFeed.getRoundData(roundId);
        return response;
    }

    function _calculateEma(uint256 newPrice, uint256 lastPrice) internal view returns (uint256) {
        return (newPrice * SMOOTHING_FACTOR) + (lastPrice * (1e18 - SMOOTHING_FACTOR)) / 1e18;
    }

    function _getEmaFromPrevious()
        internal
        view
        returns (uint256 currentPrice, ChainlinkResponse memory latestResponse)
    {
        uint256 currentObservation = _getCurrentObservationTimestamp();
        uint256 storedObservation = storedObservationTimestamp;
        uint256 currentPrice = storedPrice;
        if (currentObservation == storedObservation) return (currentPrice, latestResponse);

        bool isLatestResponse;
        latestResponse = _getLatestRoundData();
        ChainlinkResponse memory response = storedResponse;
        ChainlinkResponse memory nextResponse;
        if (latestResponse.roundId > response.roundId + 1) {
            nextResponse = _getRoundData(response.roundId + 1);
        } else {
            nextResponse = latestResponse;
            isLatestResponse = true;
        }

        while (storedObservation <= currentObservation) {
            storedObservation += FREQUENCY;
            while (!isLatestResponse && nextResponse.updatedAt < storedObservation) {
                response = nextResponse;
                if (nextResponse.roundId == latestResponse.roundId) {
                    isLatestResponse = true;
                } else {
                    nextResponse = _getRoundData(nextResponse.roundId + 1);
                }
            }
            currentPrice = _calculateEma(uint256(response.answer), currentPrice);
        }

        return (currentPrice, latestResponse);
    }

    function _getEmaWithoutPreviousData()
        internal
        view
        returns (uint256 currentPrice, ChainlinkResponse memory latestResponse)
    {
        latestResponse = _getLatestRoundData();
        ChainlinkResponse memory response = latestResponse;

        uint256[] memory oracleResponses = new uint256[](LOOKBACK);
        uint256 observationTimestamp = _getCurrentObservationTimestamp();
        for (uint256 i = LOOKBACK - 1; i != 0; i--) {
            while (response.updatedAt > observationTimestamp) {
                response = _getRoundData(response.roundId - 1);
            }
            oracleResponses[i] = uint256(response.answer);
            observationTimestamp -= FREQUENCY;
        }
        currentPrice = oracleResponses[0];
        for (uint256 i = 1; i < LOOKBACK; i++) {
            currentPrice = _calculateEma(oracleResponses[i], currentPrice);
        }
        return (currentPrice, latestResponse);
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
