// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import {
    MessagingParams,
    MessagingFee,
    MessagingReceipt
} from "@layerzerolabs/lz-evm-protocol-v2/contracts/interfaces/ILayerZeroEndpointV2.sol";

contract LzEndpointMock {
    uint32 public immutable eid;

    uint256 internal _nativeFee;

    event MessageSent(uint32 dstEid, bytes32 receiver, bytes message, bytes options);

    constructor(uint32 eid_, uint256 nativeFee_) {
        eid = eid_;
        _nativeFee = nativeFee_;
    }

    function setDelegate(address delegate) external {}

    function quote(MessagingParams calldata _params, address _sender) external view returns (MessagingFee memory) {
        return MessagingFee({ nativeFee: _nativeFee, lzTokenFee: 0 });
    }

    function send(
        MessagingParams calldata _params,
        address _refundAddress
    ) external payable returns (MessagingReceipt memory) {
        require(msg.value >= _nativeFee, "LzEndpointMock: Insufficient fee");
        if (msg.value > _nativeFee) _refundAddress.call{ value: msg.value - _nativeFee }("");
        emit MessageSent(_params.dstEid, _params.receiver, _params.message, _params.options);
    }

    fallback() external {
        revert("LzEndpointMock: Call to unmocked function");
    }
}
