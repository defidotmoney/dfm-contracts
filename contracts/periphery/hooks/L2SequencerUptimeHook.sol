// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IUptimeOracle } from "../../interfaces/IUptimeOracle.sol";

/**
    @title DFM L2 Sequencer Uptime Hook
    @author defidotmoney
    @dev Prevents increasing debt and partial withdrawal of collateral while L2
         sequencer is down or has recently restarted.
 */
contract L2SequencerUptimeHook {
    IUptimeOracle public uptimeOracle;

    constructor(IUptimeOracle _uptimeOracle) {
        uptimeOracle = _uptimeOracle;
    }

    function get_configuration() external view returns (uint256, bool[4] memory) {
        // VALIDATION_ONLY, active for `on_create_loan` and `on_adjust_loan`
        return (0, [true, true, false, false]);
    }

    function on_create_loan(
        address account,
        address market,
        uint256 collAmount,
        uint256 debtAmount
    ) external returns (int256 debtAdjustment) {
        require(uptimeOracle.getUptimeStatus(), "DFM: Sequencer down, no new loan");
        return 0;
    }

    function on_create_loan_view(
        address account,
        address market,
        uint256 collAmount,
        uint256 debtAmount
    ) external view returns (int256 debtAdjustment) {
        return 0;
    }

    function on_adjust_loan(
        address account,
        address market,
        int256 collChange,
        int256 debtChange
    ) external returns (int256 debtAdjustment) {
        if (debtChange > 0 || collChange < 0) {
            if (!uptimeOracle.getUptimeStatus()) {
                if (debtChange > 0) revert("DFM: Sequencer down, no debt++");
                else revert("DFM: Sequencer down, no coll--");
            }
        }
        return 0;
    }

    function on_adjust_loan_view(
        address account,
        address market,
        int256 collChange,
        int256 debtChange
    ) external returns (int256 debtAdjustment) {
        return 0;
    }
}
