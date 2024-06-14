// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { MessagingFee } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/interfaces/IOFT.sol";
import { OFTMsgCodec } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/libs/OFTMsgCodec.sol";
import { OFT } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/OFT.sol";
import { OAppCore } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oapp/OAppCore.sol";
import { IOAppMsgInspector } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oapp/interfaces/IOAppMsgInspector.sol";
import { ERC20FlashMint } from "@openzeppelin/contracts/token/ERC20/extensions/ERC20FlashMint.sol";
import { ERC20Permit } from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import { EnumerableSet } from "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
import { IProtocolCore } from "../interfaces/IProtocolCore.sol";
import { IBridgeToken } from "../interfaces/IBridgeToken.sol";
import { Peer } from "./dependencies/DataStructures.sol";

/**
    @title Bridge Token
    @author defidotmoney
    @notice OFT-enabled ERC20 for use in defi.money
 */
contract BridgeToken is IBridgeToken, OFT, ERC20FlashMint, ERC20Permit {
    using EnumerableSet for EnumerableSet.UintSet;

    IProtocolCore public immutable CORE_OWNER;
    uint32 public immutable thisId;

    EnumerableSet.UintSet private __eids;

    bytes public defaultOptions;
    bool public isBridgeEnabled;
    bool public isFlashMintEnabled;

    mapping(address => bool) public isMinter;

    event MinterSet(address minter, bool isApproved);
    event BridgeEnabledSet(address caller, bool isEnabled);
    event FlashMintEnabledSet(address caller, bool isEnabled);

    /**
        @notice Contract constructor
        @dev LayerZero's endpoint delegate is left unset during deployment. If needed, the owner can
             can explicitly set via `setDelegate`. We leave unset initially because we cannot inherit
             the `CoreOwnable` ownership to an external contract, and if set implicitly it could result
             in an overlooked security hole.
        @param _core Address of the DFMProtocolCore deployment
        @param _name Full name of the token
        @param _symbol Symbol of the token
        @param _lzEndpoint Address of the LayerZero V2 endpoint on this chain. Available at:
               https://docs.layerzero.network/v2/developers/evm/technical-reference/deployed-contracts
        @param _defaultOptions Default execution options to use when for a simple token transfer.
               Recommended to set to `0x0003010011010000000000000000000000000000ea60` to forward
               60,000 gas for each token bridge message.
        @param _tokenPeers Array of (endpoint ID, remote peer address) to set initial remote peers
               for this contract. When deploying to the first chain, the array should be empty. For
               deployment on subsequent chains the array is obtained by calling `getGlobalPeers` on
               the related token on any other chain.
     */
    constructor(
        IProtocolCore _core,
        string memory _name,
        string memory _symbol,
        address _lzEndpoint,
        bytes memory _defaultOptions,
        Peer[] memory _tokenPeers
    ) OFT(_name, _symbol, _lzEndpoint, address(this)) ERC20Permit(_name) {
        CORE_OWNER = _core;
        thisId = endpoint.eid();
        _setDefaultOptions(_defaultOptions);

        uint256 length = _tokenPeers.length;
        for (uint256 i; i < length; i++) {
            _setPeer(_tokenPeers[i].eid, _tokenPeers[i].peer);
        }

        isBridgeEnabled = true;
        isFlashMintEnabled = true;
    }

    // --- external view functions ---

    function owner() public view override returns (address) {
        return CORE_OWNER.owner();
    }

    /**
        @notice Returns the maximum amount of tokens available for loan
        @dev Capped at 2**127 to prevent overflow risk within the core protocol
        @param token The address of the token that is requested
        @return The amount of token that can be loaned
     */
    function maxFlashLoan(address token) public view override returns (uint256) {
        if (token == address(this) && isFlashMintEnabled) {
            return 2 ** 127 - totalSupply();
        }
        return 0;
    }

    /**
        @notice The number of configured peers globally, including this one.
     */
    function globalPeerCount() external view returns (uint256) {
        return __eids.length() + 1;
    }

    /**
        @notice Returns an array of all known global peers, including this one.
        @dev * Calling this method on an already deployed contract gives the peers
               that must be set when deploying to a new chain.
             * To check for configuration issues, compare outputs for this method
               across each chain. With a proper configuration, the output of this
               method converted to a set should be identical across all chains.
     */
    function getGlobalPeers() external view returns (Peer[] memory _peers) {
        uint256 size = __eids.length();

        _peers = new Peer[](size + 1);

        for (uint256 i; i < size; i++) {
            uint32 eid = uint32(__eids.at(i));
            _peers[i] = Peer({ eid: eid, peer: peers[eid] });
        }
        _peers[size] = Peer({ eid: thisId, peer: _addressToBytes32(address(this)) });
        return _peers;
    }

    /**
        @notice Simplified version of `OFT.quoteSend`
        @dev Uses default messaging options, assumes destination chain is EVM compatible
             and that bridge fee is paid in the chain's native token.
        @param _eid Endpoint ID of the remote chain to bridge tokens to.
        @param _target Target address to receive tokens on destination chain.
        @param _amount Amount of tokens to bridge.
        @return nativeFee Required fee amount in chain's native gas token.
     */
    function quoteSimple(uint32 _eid, address _target, uint256 _amount) external view returns (uint256) {
        (, uint256 amountReceivedLD) = _debitView(_amount, 0, _eid);
        require(amountReceivedLD > 0, "DFM:T 0 after precision loss");

        (bytes memory message, ) = OFTMsgCodec.encode(_addressToBytes32(_target), _toSD(amountReceivedLD), bytes(""));
        return _quote(_eid, message, enforcedOptions[_eid][1], false).nativeFee;
    }

    // --- unguarded external functions ---

    /**
        @notice Simplified version of `OFT.send`
        @dev Assumes destination chain is EVMcompatible, uses default options, gives
             `msg.value` as the bridge fee and refunds excess fees to the caller.
        @param _eid Endpoint ID of the remote chain to bridge tokens to.
        @param _target Target address to receive tokens on destination chain.
        @param _amount Amount of tokens to bridge.
        @return amountSentLD Actual amount of tokens that were bridged.
     */
    function sendSimple(uint32 _eid, address _target, uint256 _amount) external payable returns (uint256) {
        (uint256 amountSentLD, uint256 amountReceivedLD) = _debit(msg.sender, _amount, 0, _eid);
        require(amountReceivedLD > 0, "DFM:T 0 after precision loss");

        (bytes memory message, ) = OFTMsgCodec.encode(_addressToBytes32(_target), _toSD(amountReceivedLD), bytes(""));
        bytes memory options = enforcedOptions[_eid][1];

        // @dev Optionally inspect the message and options depending if the OApp owner has set a msg inspector.
        // @dev If it fails inspection, needs to revert in the implementation. ie. does not rely on return boolean
        if (msgInspector != address(0)) IOAppMsgInspector(msgInspector).inspect(message, options);

        bytes32 guid = _lzSend(_eid, message, options, MessagingFee(msg.value, 0), msg.sender).guid;

        emit OFTSent(guid, _eid, msg.sender, amountSentLD, amountReceivedLD);
        return amountSentLD;
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
        @notice Sets the related token address for a corresponding endpoint.
        @dev Callable by the owner as well as the bridge relay (to support
             configuration via a remote message).
        @param _eid The endpoint ID
        @param _peer Address of the peer to be associated with the endpoint.
                     Stored as a bytes32 to accommodate non-EVM chains.
     */
    function setPeer(uint32 _eid, bytes32 _peer) public override(OAppCore, IBridgeToken) {
        require(
            msg.sender == CORE_OWNER.owner() || msg.sender == CORE_OWNER.bridgeRelay(),
            "DFM:T Only owner or relay"
        );
        _setPeer(_eid, _peer);
    }

    /**
        @notice Set the remote peer for multiple endpoints
        @param _peers Array of (endpoint ID, remote peer address)
     */
    function setPeers(Peer[] calldata _peers) external onlyOwner {
        uint256 length = _peers.length;
        for (uint256 i; i < length; i++) {
            _setPeer(_peers[i].eid, _peers[i].peer);
        }
    }

    /**
        @notice Set default execution options for simple messages
        @dev https://docs.layerzero.network/v2/developers/evm/oft/quickstart#message-execution-options
             Use `0x0003010011010000000000000000000000000000ea60` to send 60,000 gas for each message.
     */
    function setDefaultOptions(bytes memory options) external onlyOwner {
        _setDefaultOptions(options);
    }

    /**
        @notice Enable or disable bridge actions for this token.
        @dev Enabled by default on deployment. Only the owner can enable.
             Both the owner and guardian can disable.
     */
    function setBridgeEnabled(bool _isEnabled) external {
        _onlyOwnerOrGuardian(_isEnabled);
        isBridgeEnabled = _isEnabled;

        emit BridgeEnabledSet(msg.sender, _isEnabled);
    }

    /**
        @notice Enable or disable flashmints of this token.
        @dev Enabled by default on deployment. Only the owner can enable.
             Both the owner and guardian can disable.
     */
    function setFlashMintEnabled(bool _isEnabled) external {
        _onlyOwnerOrGuardian(_isEnabled);
        isFlashMintEnabled = _isEnabled;

        emit FlashMintEnabledSet(msg.sender, _isEnabled);
    }

    // --- external overrides for non-implemented functionality ---

    /**
        @dev OFT inherits from `Ownable`, so we override this function
             to explicitly show that it has no effect.
     */
    function transferOwnership(address) public override {
        revert("DFM:T Owned by CORE_OWNER");
    }

    /**
        @dev OFT inherits from `Ownable`, so we override this function
             to explicitly show that it has no effect.
     */
    function renounceOwnership() public override {
        revert("DFM:T Owned by CORE_OWNER");
    }

    // --- internal functions ---

    /** @dev Internal function to perform a debit operation. Inherited from `OFT`. */
    function _debit(
        address _from,
        uint256 _amountLD,
        uint256 _minAmountLD,
        uint32 _dstEid
    ) internal override returns (uint256 amountSentLD, uint256 amountReceivedLD) {
        require(isBridgeEnabled, "DFM:T Bridging disabled");
        return super._debit(_from, _amountLD, _minAmountLD, _dstEid);
    }

    /** @dev Internal function to perform a credit operation. Inherited from `OFT`. */
    function _credit(
        address _to,
        uint256 _amountLD,
        uint32 _srcEid
    ) internal override returns (uint256 amountReceivedLD) {
        require(isBridgeEnabled, "DFM:T Bridging disabled");
        return super._credit(_to, _amountLD, _srcEid);
    }

    /** @dev Convert address to layerzero-formatted bytes32 peer */
    function _addressToBytes32(address account) internal pure returns (bytes32) {
        return bytes32(uint256(uint160(account)));
    }

    function _setPeer(uint32 _eid, bytes32 _peer) internal override {
        if (_eid == thisId) {
            // In case of a reconfiguration of many peers, validate that the local
            // peer is correct but do not store it as a remote peer. This way we
            // can safely use the output of `getGlobalPeers` across all chains.
            require(_addressToBytes32(address(this)) == _peer, "DFM: Incorrect local peer");
            return;
        }

        if (_peer == bytes32(0)) __eids.remove(_eid);
        else {
            __eids.add(_eid);
            enforcedOptions[_eid][1] = defaultOptions;
        }
        peers[_eid] = _peer;
        emit PeerSet(_eid, _peer);
    }

    function _setDefaultOptions(bytes memory options) internal {
        if (options.length > 0) _assertOptionsType3(options);
        defaultOptions = options;
    }

    function _onlyOwnerOrGuardian(bool _isEnabled) internal {
        if (msg.sender != owner()) {
            if (msg.sender == CORE_OWNER.guardian()) {
                require(!_isEnabled, "DFM:T Guardian can only disable");
            } else {
                revert("DFM:T Not owner or guardian");
            }
        }
    }
}
