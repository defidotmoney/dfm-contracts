// SPDX-License-Identifier: MIT

pragma solidity 0.8.24;

import "./interfaces/ICoreOwner.sol";
import "@layerzero-v2-oapp/contracts/oft/OFT.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20FlashMint.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";

contract StableCoin is OFT, ERC20FlashMint {
    using EnumerableSet for EnumerableSet.UintSet;

    ICoreOwner public immutable CORE_OWNER;

    EnumerableSet.UintSet private __eids;
    mapping(address => bool) public isMinter;

    constructor(
        ICoreOwner _core,
        string memory _name,
        string memory _symbol,
        address _lzEndpoint
    ) OFT(_name, _symbol, _lzEndpoint, msg.sender) Ownable(msg.sender) {
        CORE_OWNER = _core;
    }

    modifier onlyMinter() {
        require(isMinter[msg.sender], "Caller not approved to mint/burn");
        _;
    }

    function setMinter(
        address minter,
        bool isApproved
    ) external onlyOwner returns (bool) {
        isMinter[minter] = isApproved;
        return true;
    }

    function mint(
        address _to,
        uint256 _value
    ) external onlyMinter returns (bool) {
        _mint(_to, _value);
        return true;
    }

    function burn(address _to, uint256 _value) external returns (bool) {
        if (msg.sender != _to)
            require(isMinter[msg.sender], "Caller not approved to mint/burn");
        _burn(_to, _value);
        return true;
    }

    function setPeer(uint32 _eid, bytes32 _peer) public override onlyOwner {
        _setPeer(_eid, _peer);
    }

    function setPeers(
        uint32[] calldata _eids,
        bytes32[] calldata _peers
    ) external onlyOwner {
        require(_eids.length == _peers.length && _eids.length != 0);

        for (uint256 i; i < _eids.length; i++) {
            _setPeer(_eids[i], _peers[i]);
        }
    }

    function _setPeer(uint32 _eid, bytes32 _peer) override internal {
        bool update = false;
        bytes32 peer = peers[_eid];

        assembly {
            update := xor(iszero(peer), iszero(_peer))
        }

        if (update) {
            if (_peer == bytes32(0)) {
                __eids.remove(_eid);
            } else {
                __eids.add(_eid);
            }
        }

        peers[_eid] = _peer;
        emit PeerSet(_eid, _peer);
    }

    function getPeers()
        external
        view
        returns (uint32[] memory, bytes32[] memory)
    {
        uint256 size = __eids.length();

        uint32[] memory eids = new uint32[](size);
        bytes32[] memory _peers = new bytes32[](size);

        for (uint256 i; i < size; i++) {
            uint32 eid = uint32(__eids.at(i));
            eids[i] = eid;
            _peers[i] = peers[eid];
        }
        return (eids, _peers);
    }

    function owner() public view override returns (address) {
        return CORE_OWNER.owner();
    }
}
