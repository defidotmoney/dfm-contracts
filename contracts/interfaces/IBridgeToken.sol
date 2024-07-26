// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import { IERC3156FlashLender } from "@openzeppelin/contracts/interfaces/IERC3156FlashLender.sol";
import { IBridgeTokenBase } from "./IBridgeTokenBase.sol";

interface IBridgeToken is IBridgeTokenBase, IERC3156FlashLender {
    function setMinter(address minter, bool isApproved) external returns (bool);

    function mint(address _account, uint256 _amount) external returns (bool);

    function burn(address _account, uint256 _amount) external returns (bool);
}
