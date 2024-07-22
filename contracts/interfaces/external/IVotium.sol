// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IVotium {
    function activeRound() external view returns (uint256);

    function depositSplitGauges(
        address _token,
        uint256 _amount,
        uint256 _round,
        address[] calldata _gauges,
        uint256 _maxPerVote,
        address[] calldata _excluded
    ) external;
}
