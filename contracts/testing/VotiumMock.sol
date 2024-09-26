// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { IVotium } from "../interfaces/external/IVotium.sol";

contract VotiumMock is IVotium {
    IERC20 public immutable stableCoin;

    constructor(IERC20 _stable) {
        stableCoin = _stable;
    }

    function depositUnevenSplitGaugesSimple(
        address _token,
        address[] memory _gauges,
        uint256[] memory _amounts
    ) external {
        require(_gauges.length == _amounts.length, "VotiumMock: array length mismatch");
        require(_token == address(stableCoin), "VotiumMock: wrong token");

        uint256 length = _gauges.length;
        for (uint256 i = 0; i < length; i++) {
            require(_amounts[i] > 0, "VotiumMock: zero amount");
            require(_gauges[i] != address(0), "VotiumMock: empty gauge address");
            stableCoin.transferFrom(msg.sender, address(this), _amounts[i]);
        }
    }

    function withdrawUnprocessed(uint256 _round, address _gauge, uint256 _incentive) external {
        revert("VotiumMock: Unsupported function");
    }

    fallback() external {
        revert("VotiumMock: Call to unmocked function");
    }
}
