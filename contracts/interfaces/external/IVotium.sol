// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IVotium {
    function activeRound() external view returns (uint256);

    /** @dev deposit same token to multiple gauges with different amounts in a single round */
    function depositUnevenSplitGauges(
        address _token,
        uint256 _round,
        address[] memory _gauges,
        uint256[] calldata _amounts,
        uint256 _maxPerVote,
        address[] calldata _excluded
    ) external;
}
