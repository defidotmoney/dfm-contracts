// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import { IOFT } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/interfaces/IOFT.sol";

interface IBridgeToken is IOFT {
    function setMinter(address minter, bool isApproved) external returns (bool);

    function mint(address _account, uint256 _amount) external returns (bool);

    function burn(address _account, uint256 _amount) external returns (bool);

    function quoteSimple(uint32 _eid, address _target, uint256 _amount) external view returns (uint256);

    function sendSimple(uint32 _eid, address _target, uint256 _amount) external payable returns (uint256);

    function globalPeerCount() external view returns (uint256);

    function setPeer(uint32 _eid, bytes32 _peer) external;
}
