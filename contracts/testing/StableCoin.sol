// SPDX-License-Identifier: MIT

pragma solidity 0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20FlashMint.sol";
import "@openzeppelin/contracts/access/Ownable.sol";


contract StableCoin is ERC20FlashMint, Ownable {
    mapping(address => bool) public isMinter;


    constructor() ERC20("Test Stablecoin", "STABLE") Ownable(msg.sender) {}

    modifier onlyMinter() {
        require(isMinter[msg.sender], "Caller not approved to mint/burn");
        _;
    }

    function setMinter(address minter, bool isApproved) external onlyOwner returns (bool) {
        isMinter[minter] = isApproved;
        return true;
    }

    function mint(address _to, uint256 _value) external onlyMinter returns (bool) {
        _mint(_to, _value);
        return true;
    }

    function burn(address _to, uint256 _value) external returns (bool) {
        if (msg.sender != _to) require(isMinter[msg.sender], "Caller not approved to mint/burn");
        _burn(_to, _value);
        return true;
    }

}
