// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { ERC20Permit } from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import { BridgeTokenBase } from "./dependencies/BridgeTokenBase.sol";
import { Peer } from "./dependencies/DataStructures.sol";

/**
    @title Bridge Token (Simplified)
    @author defidotmoney
    @notice OFT-enabled ERC20 for use in defi.money
    @dev Deployed as a token peer on non-primary chains where the protocol does
         not support direct minting or burning
 */
contract BridgeTokenSimple is BridgeTokenBase, ERC20Permit {
    /**
        @notice Contract constructor
        @dev see `BridgeTokenBase` natspec for info about params
     */
    constructor(
        address _core,
        string memory _name,
        string memory _symbol,
        address _lzEndpoint,
        bytes memory _defaultOptions,
        Peer[] memory _tokenPeers
    ) BridgeTokenBase(_core, _name, _symbol, _lzEndpoint, _defaultOptions, _tokenPeers) ERC20Permit(_name) {}
}
