// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IChainlinkAggregator } from "../../interfaces/IChainlinkAggregator.sol";
import { IPriceOracle } from "../../interfaces/IPriceOracle.sol";

/**
    @title Chainlink EMA Oracle
    @author defidotmoney
    @dev Calculated an exponential moving average from a Chainlink Feed
 */
contract ChainlinkEMA {
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
        uint128 updatedAt;
        uint256 answer;
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
            uint256 answer = response.answer;
            while (storedObservation < currentObservation) {
                storedObservation += FREQUENCY;
                currentPrice = _getNextEMA(answer, currentPrice);
            }
            return (currentPrice, latestResponse, false);
        }

        bool isLatestResponse;
        ChainlinkResponse memory nextResponse;
        if (latestResponse.roundId > response.roundId + 1) {
            nextResponse = _getNextRoundData(response.roundId);
        } else {
            nextResponse = latestResponse;
        }

        while (storedObservation < currentObservation) {
            storedObservation += FREQUENCY;
            while (!isLatestResponse && nextResponse.updatedAt < storedObservation) {
                response = nextResponse;
                if (nextResponse.roundId == latestResponse.roundId) {
                    isLatestResponse = true;
                } else {
                    nextResponse = _getNextRoundData(nextResponse.roundId);
                }
            }
            currentPrice = _getNextEMA(response.answer, currentPrice);
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

        // in the following while loops, we manually decrement and then increment
        // idx so we know where the first non-zero value is within oracleResponses
        uint256 idx = LOOKBACK;

        // iterate backward to get oracle responses for each observation time
        while (true) {
            while (response.updatedAt > observationTimestamp) {
                if (response.roundId & type(uint64).max == 0) {
                    // first roundId for this aggregator, cannot look back further
                    break;
                }
                response = _getRoundData(response.roundId - 1);
            }
            if (response.updatedAt > observationTimestamp) {
                if (idx == LOOKBACK) {
                    // edge case, if the first round is more recent than our latest
                    // observation time we can only return the first round's response
                    return (response.answer, latestResponse);
                }
                break;
            }
            idx--;
            oracleResponses[idx] = response.answer;
            if (idx == 0) break;
            observationTimestamp -= FREQUENCY;
        }

        // now iterate forward to calculate EMA based on the observed oracle responses
        currentPrice = oracleResponses[idx];
        idx++;
        while (idx < LOOKBACK) {
            currentPrice = _getNextEMA(oracleResponses[idx], currentPrice);
            idx++;
        }

        return (currentPrice, latestResponse);
    }

    /** @dev Given the latest price and the last EMA, returns the new EMA */
    function _getNextEMA(uint256 newPrice, uint256 lastEMA) internal view returns (uint256) {
        return ((newPrice * SMOOTHING_FACTOR) + (lastEMA * (1e18 - SMOOTHING_FACTOR))) / 1e18;
    }

    /** @dev The timestamp of the latest oracle observation */
    function _getCurrentObservationTimestamp() internal view returns (uint256) {
        return (block.timestamp / FREQUENCY) * FREQUENCY;
    }

    function _getLatestRoundData() internal view returns (ChainlinkResponse memory) {
        (uint80 roundId, int256 answer, , uint256 updatedAt, ) = chainlinkFeed.latestRoundData();
        return _validateAndFormatResponse(roundId, answer, updatedAt);
    }

    function _getRoundData(uint80 roundId) internal view returns (ChainlinkResponse memory) {
        (uint80 roundId, int256 answer, , uint256 updatedAt, ) = chainlinkFeed.getRoundData(roundId);
        return _validateAndFormatResponse(roundId, answer, updatedAt);
    }

    /**
        @dev Given a `roundId`, gets the response data for the next round. This method is preferred
             over calling `_getRoundData(roundId + 1)` because it handles a case where the oracle
             phase has increased: https://docs.chain.link/data-feeds/historical-data#roundid-in-proxy
     */
    function _getNextRoundData(uint80 roundId) internal view returns (ChainlinkResponse memory) {
        try chainlinkFeed.getRoundData(roundId + 1) returns (uint80 round, int answer, uint, uint updatedAt, uint80) {
            return _validateAndFormatResponse(round, answer, updatedAt);
        } catch {
            // handle case where chainlink phase has increased
            uint80 nextRoundId = ((roundId >> 64) + 1) << 64;
            return _getRoundData(nextRoundId);
        }
    }

    function _validateAndFormatResponse(
        uint80 roundId,
        int256 answer,
        uint256 updatedAt
    ) internal pure returns (ChainlinkResponse memory) {
        require(answer > 0, "DFM: Chainlink answer too low");
        return ChainlinkResponse({ roundId: roundId, updatedAt: uint128(updatedAt), answer: uint256(answer) });
    }
}
