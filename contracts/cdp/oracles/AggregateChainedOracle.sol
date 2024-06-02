// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "@openzeppelin/contracts/utils/Address.sol";
import "../../base/dependencies/CoreOwnable.sol";
import "../../interfaces/IPriceOracle.sol";
import "../../interfaces/IUptimeOracle.sol";

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
        // calldata input passsed to `target` to get the oracle response.
        bytes input;
    }

    OracleCall[][] private oracleCallPaths;

    IUptimeOracle public uptimeOracle;
    uint256 public storedPrice;

    constructor(address _coreOwner, IUptimeOracle _uptimeOracle) CoreOwnable(_coreOwner) {
        uptimeOracle = _uptimeOracle;
    }

    // --- IPriceOracle required interface ---

    function price() external view returns (uint256) {
        uint256 result = _maybeGetStoredPrice();
        if (result == 0) return _fetchAggregateResult();
        return result;
    }

    function price_w() external returns (uint256) {
        uint256 result = _maybeGetStoredPrice();
        if (result == 0) {
            result = _fetchAggregateResult();
            storedPrice = result;
        }
        return result;
    }

    // --- external view functions ---

    function getCallPathCount() external view returns (uint256) {
        return oracleCallPaths.length;
    }

    function getCallPath(uint256 idx) external view returns (OracleCall[] memory path) {
        return oracleCallPaths[idx];
    }

    function getCallPathResult(uint256 idx) external view returns (uint256) {
        return _fetchCallPathResult(oracleCallPaths[idx]);
    }

    // --- owner-only guarded external functions ---

    function setUptimeOracle(IUptimeOracle _uptimeOracle) external onlyOwner {
        if (address(_uptimeOracle) != address(0)) {
            require(_uptimeOracle.getUptimeStatus(), "DFM: Bad uptime answer");
        }
        uptimeOracle = _uptimeOracle;
    }

    function addCallPath(OracleCall[] calldata path) external onlyOwner {
        uint256 length = path.length;
        require(length > 0, "DFM: Cannot set empty path");

        oracleCallPaths.push();
        OracleCall[] storage storagePath = oracleCallPaths[oracleCallPaths.length - 1];
        for (uint256 i = 0; i < length; i++) {
            require(path[i].decimals != 0, "DFM: Decimals cannot be 0");
            require(path[i].decimals < 19, "DFM: Maximum 18 decimals");
            storagePath.push(path[i]);
        }
        _fetchCallPathResult(path);
    }

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
            return storedPrice;
        }
        return 0;
    }

    function _fetchAggregateResult() internal view returns (uint256 result) {
        uint256 length = oracleCallPaths.length;
        for (uint256 i = 0; i < length; i++) {
            result += _fetchCallPathResult(oracleCallPaths[i]);
        }
        return result / length;
    }

    function _fetchCallPathResult(OracleCall[] memory path) internal view returns (uint256 result) {
        result = 1e18;
        uint256 length = path.length;
        for (uint256 i = 0; i < length; i++) {
            uint256 answer = uint256(bytes32(path[i].target.functionStaticCall(path[i].input)));
            require(answer != 0, "DFM: Oracle returned 0");
            answer *= 10 ** (18 - path[i].decimals);
            if (path[i].isMultiplied) result = (result * answer) / 1e18;
            else result = (result * 1e18) / answer;
        }
        return result;
    }
}
