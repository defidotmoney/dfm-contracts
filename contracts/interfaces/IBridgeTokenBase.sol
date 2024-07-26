// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import { IOFT } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/interfaces/IOFT.sol";
import { IOAppCore } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oapp/interfaces/IOAppCore.sol";
import { IERC20Metadata } from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";

interface IBridgeTokenBase is IOFT, IOAppCore, IERC20Metadata {
    function quoteSimple(uint32 _eid, address _target, uint256 _amount) external view returns (uint256);

    function sendSimple(uint32 _eid, address _target, uint256 _amount) external payable returns (uint256);

    function globalPeerCount() external view returns (uint256);

    function setPeer(uint32 _eid, bytes32 _peer) external;

    function thisId() external view returns (uint32);

    function defaultOptions() external view returns (bytes memory);
}
