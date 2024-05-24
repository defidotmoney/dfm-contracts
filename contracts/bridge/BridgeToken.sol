// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/OFT.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20FlashMint.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
import "../interfaces/IProtocolCore.sol";
import { Peer } from "./dependencies/DataStructures.sol";

/**
    @title Bridge Token
    @author defidotmoney
    @notice OFT-enabled ERC20 for use in defi.money
 */
contract BridgeToken is OFT, ERC20FlashMint {
    using EnumerableSet for EnumerableSet.UintSet;

    IProtocolCore public immutable CORE_OWNER;

    EnumerableSet.UintSet private __eids;

    bytes public defaultOptions;

    mapping(address => bool) public isMinter;

    event MinterSet(address minter, bool isApproved);

    constructor(
        IProtocolCore _core,
        string memory _name,
        string memory _symbol,
        address _lzEndpoint,
        bytes memory _defaultOptions // 0x0003010011010000000000000000000000000000ea60
    ) OFT(_name, _symbol, _lzEndpoint, msg.sender) {
        CORE_OWNER = _core;
        _setDefaultOptions(_defaultOptions);
    }

    function setMinter(address minter, bool isApproved) external onlyOwner returns (bool) {
        isMinter[minter] = isApproved;
        emit MinterSet(minter, isApproved);
        return true;
    }

    function mint(address _account, uint256 _amount) external returns (bool) {
        require(isMinter[msg.sender], "DFM:T Not approved to mint");
        _mint(_account, _amount);
        return true;
    }

    function burn(address _account, uint256 _amount) external returns (bool) {
        if (msg.sender != _account) require(isMinter[msg.sender], "DFM:T Not approved to burn");
        _burn(_account, _amount);
        return true;
    }

    function setPeer(uint32 _eid, bytes32 _peer) public override {
        require(
            msg.sender == CORE_OWNER.owner() || msg.sender == CORE_OWNER.bridgeRelay(),
            "DFM:T Only owner or relay"
        );
        _setPeer(_eid, _peer);
    }

    function setPeers(Peer[] calldata _peers) external onlyOwner {
        uint256 length = _peers.length;
        for (uint256 i; i < length; i++) {
            _setPeer(_peers[i].eid, _peers[i].peer);
        }
    }

    /**
        @notice Set default execution options for simple messages
        @dev https://docs.layerzero.network/v2/developers/evm/oft/quickstart#message-execution-options
             Use `0x0003010011010000000000000000000000000000ea60` to send
             60,000 gas for each token bridge message.

     */
    function setDefaultOptions(bytes memory options) external onlyOwner {
        _setDefaultOptions(options);
    }

    function _setPeer(uint32 _eid, bytes32 _peer) internal override {
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

    function getPeers() external view returns (uint32[] memory, bytes32[] memory) {
        uint256 size = __eids.length();

        uint32[] memory _eids = new uint32[](size);
        bytes32[] memory _peers = new bytes32[](size);

        uint32 eid = 0;
        for (uint256 i; i < size; i++) {
            _eids[i] = (eid = uint32(__eids.at(i)));
            _peers[i] = peers[eid];
        }
        return (_eids, _peers);
    }

    function maxFlashLoan(address token) public view override returns (uint256) {
        return token == address(this) ? 2 ** 127 - totalSupply() : 0;
    }

    function owner() public view override returns (address) {
        return CORE_OWNER.owner();
    }

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
}
