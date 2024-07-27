// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { ERC20FlashMint } from "@openzeppelin/contracts/token/ERC20/extensions/ERC20FlashMint.sol";
import { ERC20Permit } from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import { IERC3156FlashLender } from "@openzeppelin/contracts/interfaces/IERC3156FlashLender.sol";
import { IBridgeToken } from "../interfaces/IBridgeToken.sol";
import { IBridgeTokenBase } from "../interfaces/IBridgeTokenBase.sol";
import { Peer } from "./dependencies/DataStructures.sol";
import { BridgeTokenBase } from "./dependencies/BridgeTokenBase.sol";

/**
    @title Bridge Token
    @author defidotmoney
    @notice OFT-enabled ERC20 for use in defi.money
    @dev Standard implementation for protocol omni-chain tokens (mintable on any chain)
 */
contract BridgeToken is IBridgeToken, BridgeTokenBase, ERC20FlashMint, ERC20Permit {
    bool public isFlashMintEnabled;

    mapping(address => bool) public isMinter;

    event MinterSet(address minter, bool isApproved);
    event FlashMintEnabledSet(address caller, bool isEnabled);

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
    ) BridgeTokenBase(_core, _name, _symbol, _lzEndpoint, _defaultOptions, _tokenPeers) ERC20Permit(_name) {
        isFlashMintEnabled = true;
    }

    // --- external view functions ---

    /**
        @notice Returns the maximum amount of tokens available for loan
        @dev Capped at 2**127 to prevent overflow risk within the core protocol
        @param token The address of the token that is requested
        @return The amount of token that can be loaned
     */
    function maxFlashLoan(address token) public view override(ERC20FlashMint, IERC3156FlashLender) returns (uint256) {
        if (token == address(this) && isFlashMintEnabled) {
            return 2 ** 127 - totalSupply();
        }
        return 0;
    }

    // --- guarded external functions ---

    /**
        @notice Set minter permissions a given address
        @dev Only callable by the owner. Minter permission should only be given
             to specific contracts within the system that absolutely require it,
             and only when their functionality is completely understood.
        @param minter Address to set permissions for
        @param isApproved Is the contract approved to mint?
     */
    function setMinter(address minter, bool isApproved) external onlyOwner returns (bool) {
        isMinter[minter] = isApproved;
        emit MinterSet(minter, isApproved);
        return true;
    }

    /**
        @notice Mint new tokens for a given address
        @dev Only callable by accounts that have been permitted via `setMinter`
        @param _account Account to mint tokens for
        @param _amount Amount of tokens to mint
     */
    function mint(address _account, uint256 _amount) external returns (bool) {
        require(isMinter[msg.sender], "DFM:T Not approved to mint");
        _mint(_account, _amount);
        return true;
    }

    /**
        @notice Burn a token balance at a given address
        @dev Any account may call to burn their own token balance. Only accounts
             with minter permission may call to burn tokens for another account.
        @param _account Account to burn tokens for
        @param _amount Amount of tokens to burn
     */
    function burn(address _account, uint256 _amount) external returns (bool) {
        if (msg.sender != _account) require(isMinter[msg.sender], "DFM:T Not approved to burn");
        _burn(_account, _amount);
        return true;
    }

    /**
        @notice Enable or disable flashmints of this token.
        @dev Enabled by default on deployment. Only the owner can enable.
             Both the owner and guardian can disable.
     */
    function setFlashMintEnabled(bool _isEnabled) external onlyOwnerOrGuardian(_isEnabled) {
        isFlashMintEnabled = _isEnabled;
        emit FlashMintEnabledSet(msg.sender, _isEnabled);
    }

    function setPeer(uint32 _eid, bytes32 _peer) public override(BridgeTokenBase, IBridgeTokenBase) {
        BridgeTokenBase.setPeer(_eid, _peer);
    }
}
