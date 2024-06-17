// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { Address } from "@openzeppelin/contracts/utils/Address.sol";
import { CoreOwnable } from "../../base/dependencies/CoreOwnable.sol";
import { IPriceOracle } from "../../interfaces/IPriceOracle.sol";
import { IUptimeOracle } from "../../interfaces/IUptimeOracle.sol";

/**
    @title Aggregate Chained Oracle
    @author defidotmoney
    @notice Returns the average price from one or more sequences of oracle calls,
            with price caching and an optional `UptimeOracle` call.
 */
contract AggregateChainedOracle is IPriceOracle, CoreOwnable {
    using Address for address;

    struct OracleCall {
        // Address of the oracle to call.
        address target;
        // Decimal precision of response. Cannot be greater than 18.
        uint8 decimals;
        // If `true`, the new price is calculated from the answer as `result * answer / 1e18`
        // If `false, the calculation is `result * 1e18 / answer`
        bool isMultiplied;
        // Calldata input passsed to `target` to get the oracle response in a staticcall context.
        bytes inputView;
        // Calldata input passsed to `target` to get the oracle response in a write context.
        // In some cases this might be the same value as `inputView`.
        bytes inputWrite;
    }

    OracleCall[][] private oracleCallPaths;

    IUptimeOracle public uptimeOracle;
    uint256 public storedPrice;

    constructor(address _coreOwner, IUptimeOracle _uptimeOracle) CoreOwnable(_coreOwner) {
        uptimeOracle = _uptimeOracle;
    }

    // --- IPriceOracle required interface ---

    /**
        @notice The current oracle price, normalized to 1e18 precision
        @dev Read-only version used within view methods
     */
    function price() external view returns (uint256) {
        uint256 result = _maybeGetStoredPrice();
        if (result != 0) return result;
        uint256 length = oracleCallPaths.length;
        for (uint256 i = 0; i < length; i++) {
            result += _fetchCallPathResultView(oracleCallPaths[i]);
        }
        return result / length;
    }

    /**
        @notice The current oracle price, normalized to 1e18 precision
        @dev Write version that also stores the price. The stored price is
             returned later if the uptime oracle reports a downtime.
     */
    function price_w() external returns (uint256) {
        uint256 result = _maybeGetStoredPrice();
        if (result != 0) return result;

        uint256 length = oracleCallPaths.length;
        for (uint256 i = 0; i < length; i++) {
            result += _fetchCallPathResultWrite(oracleCallPaths[i]);
        }
        result = result / length;
        storedPrice = result;

        return result;
    }

    // --- external view functions ---

    /**
        @notice Get the current number of oracle call paths
        @return count Number of oracle call paths
     */
    function getCallPathCount() external view returns (uint256 count) {
        return oracleCallPaths.length;
    }

    /**
        @notice Get an array of `OracleCall` tuples that collectively
                form one oracle call path
        @param idx Index of the oracle call path
        @return path Dynamic array of `OracleCall` tuples
     */
    function getCallPath(uint256 idx) external view returns (OracleCall[] memory path) {
        return oracleCallPaths[idx];
    }

    /**
        @notice Fetches the current view response for a single oracle call path
        @param idx Index of the oracle call path to query
        @return response Oracle call path view response
     */
    function getCallPathResult(uint256 idx) external view returns (uint256 response) {
        return _fetchCallPathResultView(oracleCallPaths[idx]);
    }

    // --- unguarded external functions ---

    /**
        @notice Fetches the current write response for a single oracle call path
        @param idx Index of the oracle call path to query
        @return response Oracle call path write response
     */
    function getCallPathResultWrite(uint256 idx) external returns (uint256 response) {
        return _fetchCallPathResultWrite(oracleCallPaths[idx]);
    }

    // --- owner-only guarded external functions ---

    function setUptimeOracle(IUptimeOracle _uptimeOracle) external onlyOwner {
        if (address(_uptimeOracle) != address(0)) {
            require(_uptimeOracle.getUptimeStatus(), "DFM: Bad uptime answer");
        }
        uptimeOracle = _uptimeOracle;
    }

    /**
        @notice Add a new sequence of 1 or more oracle calls
        @dev When querying a price from this contract, each "oracle call path"
             is executed independently. The final returned price is an average
             of the values returned from each path.
        @param path Dynamic array of one or more `OraclePath` structs. The
                    comments in the struct definition explain the layout.
     */
    function addCallPath(OracleCall[] calldata path) external onlyOwner {
        uint256 length = path.length;
        require(length > 0, "DFM: Cannot set empty path");

        oracleCallPaths.push();
        OracleCall[] storage storagePath = oracleCallPaths[oracleCallPaths.length - 1];
        for (uint256 i = 0; i < length; i++) {
            require(path[i].decimals < 19, "DFM: Maximum 18 decimals");
            storagePath.push(path[i]);
        }

        uint256 resultView = _fetchCallPathResultView(path);
        uint256 resultWrite = _fetchCallPathResultWrite(path);
        require(resultView == resultWrite, "DFM: view != write");
    }

    /**
        @notice Remove an oracle call path
        @dev Once a path has been set, the contract cannot ever return to a
             state where there is no set path. If you wish to remove the last
             path you should first add a new path that will replace it.
        @param idx Index of the oracle call path to remove
     */
    function removeCallPath(uint256 idx) external onlyOwner {
        uint256 length = oracleCallPaths.length;
        require(idx < length, "DFM: Invalid path index");
        require(length > 1, "DFM: Cannot remove only path");
        if (idx < length - 1) {
            oracleCallPaths[idx] = oracleCallPaths[length - 1];
        }
        oracleCallPaths.pop();
    }

    // --- internal functions ---

    function _maybeGetStoredPrice() internal view returns (uint256 response) {
        IUptimeOracle oracle = uptimeOracle;
        if (address(oracle) != address(0) && !oracle.getUptimeStatus()) {
            // If uptime oracle is set and currently reports downtime,
            // return the last stored price
            return storedPrice;
        }
        // Otherwise return 0 to indicate that a new price should be queried
        return 0;
    }

    function _fetchCallPathResultView(OracleCall[] memory path) internal view returns (uint256 result) {
        result = 1e18;
        uint256 length = path.length;
        for (uint256 i = 0; i < length; i++) {
            uint256 answer = uint256(bytes32(path[i].target.functionStaticCall(path[i].inputView)));
            require(answer != 0, "DFM: Oracle returned 0");
            answer *= 10 ** (18 - path[i].decimals);
            if (path[i].isMultiplied) result = (result * answer) / 1e18;
            else result = (result * 1e18) / answer;
        }
        return result;
    }

    function _fetchCallPathResultWrite(OracleCall[] memory path) internal returns (uint256 result) {
        result = 1e18;
        uint256 length = path.length;
        for (uint256 i = 0; i < length; i++) {
            uint256 answer = uint256(bytes32(path[i].target.functionCall(path[i].inputWrite)));
            require(answer != 0, "DFM: Oracle returned 0");
            answer *= 10 ** (18 - path[i].decimals);
            if (path[i].isMultiplied) result = (result * answer) / 1e18;
            else result = (result * 1e18) / answer;
        }
        return result;
    }
}
