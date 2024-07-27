// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import {
    MessagingParams,
    MessagingFee,
    MessagingReceipt,
    Origin
} from "@layerzerolabs/lz-evm-protocol-v2/contracts/interfaces/ILayerZeroEndpointV2.sol";
import { ILayerZeroReceiver } from "@layerzerolabs/lz-evm-protocol-v2/contracts/interfaces/ILayerZeroReceiver.sol";
import { OFTMsgCodec } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/libs/OFTMsgCodec.sol";

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
        _assertOptionsType3(_params.options);
        if (msg.value > _nativeFee) {
            (bool success, ) = _refundAddress.call{ value: msg.value - _nativeFee }("");
            require(success, "LzEndpointMock: Gas refund transfer failed");
        }

        emit MessageSent(_params.dstEid, _params.receiver, _params.message, _params.options);
    }

    function _assertOptionsType3(bytes calldata _options) internal pure virtual {
        uint16 optionsType = uint16(bytes2(_options[0:2]));
        require(optionsType == 3, "LzEndpointMock: Invalid options");
    }

    /** @dev Assumes that the token uses 18 decimals */
    function mockMintTokens(ILayerZeroReceiver token, address receiver, uint32 srcId, uint256 amount) external {
        bytes32 receiverBytes = OFTMsgCodec.addressToBytes32(receiver);
        (bytes memory message, ) = OFTMsgCodec.encode(receiverBytes, uint64(amount / 10 ** 12), bytes(""));
        Origin memory origin = Origin(srcId, OFTMsgCodec.addressToBytes32(address(token)), 0);
        token.lzReceive(origin, bytes32(0), message, msg.sender, bytes(""));
    }

    fallback() external {
        revert("LzEndpointMock: Call to unmocked function");
    }
}
