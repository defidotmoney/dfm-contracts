// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import { IOFT } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/interfaces/IOFT.sol";
import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { IERC3156FlashLender } from "@openzeppelin/contracts/interfaces/IERC3156FlashLender.sol";

interface IBridgeToken is IOFT, IERC20, IERC3156FlashLender {
    function setMinter(address minter, bool isApproved) external returns (bool);

    function mint(address _account, uint256 _amount) external returns (bool);

    function burn(address _account, uint256 _amount) external returns (bool);

    function quoteSimple(uint32 _eid, address _target, uint256 _amount) external view returns (uint256);

    function sendSimple(uint32 _eid, address _target, uint256 _amount) external payable returns (uint256);

    function globalPeerCount() external view returns (uint256);

    function setPeer(uint32 _eid, bytes32 _peer) external;
}
