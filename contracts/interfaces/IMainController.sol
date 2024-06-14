// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IMainController {
    function get_collateral(address market) external view returns (address);

    function get_oracle_price(address collateral) external view returns (uint256);

    function get_close_loan_amounts(
        address account,
        address market
    ) external view returns (int256 callerDebtBalanceChange, uint256 collReceived);

    function create_loan(
        address account,
        address market,
        uint256 collAmount,
        uint256 debtAmount,
        uint256 numBands
    ) external;

    function adjust_loan(address account, address market, int256 collChange, int256 debtChange) external;

    function close_loan(address account, address market) external;
}
