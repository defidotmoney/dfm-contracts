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

        uint256 currentObservation = _getCurrentObservationTimestamp();
        (storedPrice, storedResponse) = _calculateNewEMA(currentObservation);
        storedObservationTimestamp = currentObservation;
    }

    /**
        @notice Returns the current oracle price, normalized to 1e18 precision
        @dev Read-only version used within view methods. Should always return
             the same value as `price_w`
     */
    function price() external view returns (uint256 currentPrice) {
        uint256 currentObservation = _getCurrentObservationTimestamp();
        uint256 storedObservation = storedObservationTimestamp;
        if (currentObservation == storedObservation) return storedPrice;

        if (storedObservation + LOOKBACK * FREQUENCY > currentObservation) {
            (currentPrice, , ) = _calculateLatestEMA(currentObservation, storedObservation);
        } else {
            (currentPrice, ) = _calculateNewEMA(currentObservation);
        }
        return currentPrice;
    }

    /**
        @notice Returns the current oracle price, normalized to 1e18 precision
        @dev Called by all state-changing market / amm operations with the exception
             of `MainController.close_loan`
     */
    function price_w() external returns (uint256 currentPrice) {
        uint256 currentObservation = _getCurrentObservationTimestamp();
        uint256 storedObservation = storedObservationTimestamp;
        if (currentObservation == storedObservation) return storedPrice;

        if (storedObservation + LOOKBACK * FREQUENCY > currentObservation) {
            bool isNewResponse;
            ChainlinkResponse memory response;
            (currentPrice, response, isNewResponse) = _calculateLatestEMA(currentObservation, storedObservation);
            if (isNewResponse) storedResponse = response;
        } else {
            (currentPrice, storedResponse) = _calculateNewEMA(currentObservation);
        }
        storedObservationTimestamp = currentObservation;
        storedPrice = currentPrice;
        return currentPrice;
    }

    /**
        @dev Calculates the latest EMA price by performing observations at all observation
             intervals since the last stored one. Used when the number of new observations
             required is less than `2 * OBSERVATIONS`.
     */
    function _calculateLatestEMA(
        uint256 currentObservation,
        uint256 storedObservation
    ) internal view returns (uint256 currentPrice, ChainlinkResponse memory latestResponse, bool isNewResponse) {
        currentPrice = storedPrice;
        latestResponse = _getLatestRoundData();
        ChainlinkResponse memory response = storedResponse;

        // special case, latest round is the same as stored round
        if (latestResponse.roundId == response.roundId) {
            uint256 answer = uint256(response.answer);
            while (storedObservation <= currentObservation) {
                storedObservation += FREQUENCY;
                currentPrice = _getNextEMA(answer, currentPrice);
            }
            return (currentPrice, latestResponse, false);
        }

        bool isLatestResponse;
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
            currentPrice = _getNextEMA(uint256(response.answer), currentPrice);
        }

        return (currentPrice, latestResponse, true);
    }

    /**
        @dev Calculates an EMA price without relying on the last stored observation.
             Used when the number of new observations required is at least `2 * OBSERVATIONS`.
     */
    function _calculateNewEMA(
        uint256 observationTimestamp
    ) internal view returns (uint256 currentPrice, ChainlinkResponse memory latestResponse) {
        latestResponse = _getLatestRoundData();
        ChainlinkResponse memory response = latestResponse;

        uint256[] memory oracleResponses = new uint256[](LOOKBACK);
        for (uint256 i = LOOKBACK - 1; i != 0; i--) {
            while (response.updatedAt > observationTimestamp) {
                response = _getRoundData(response.roundId - 1);
            }
            oracleResponses[i] = uint256(response.answer);
            observationTimestamp -= FREQUENCY;
        }
        currentPrice = oracleResponses[0];
        for (uint256 i = 1; i < LOOKBACK; i++) {
            currentPrice = _getNextEMA(oracleResponses[i], currentPrice);
        }
        return (currentPrice, latestResponse);
    }

    /** @dev Given the latest price and the last EMA, returns the new EMA */
    function _getNextEMA(uint256 newPrice, uint256 lastEMA) internal view returns (uint256) {
        return (newPrice * SMOOTHING_FACTOR) + (lastEMA * (1e18 - SMOOTHING_FACTOR)) / 1e18;
    }

    /** @dev The timestamp of the latest oracle observation */
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
}
