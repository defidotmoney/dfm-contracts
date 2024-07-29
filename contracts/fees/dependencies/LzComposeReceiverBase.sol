// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import { ILayerZeroComposer } from "@layerzerolabs/lz-evm-protocol-v2/contracts/interfaces/ILayerZeroComposer.sol";
import { OFTComposeMsgCodec } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/libs/OFTComposeMsgCodec.sol";

/**
    @notice LzCompose Receiver Abstract Base
    @author defidotmoney
    @dev Base logic for fee receiver contracts deployed to non-primary chains,
         that receive fees via `LzComposeForwarder`
 */

abstract contract LzComposeReceiverBase is ILayerZeroComposer {
    address public immutable endpoint;
    address public immutable oApp;
    bytes32 public immutable remoteCaller;
    bool public immutable allowPayableLzCompose;

    event NotifyNewFees(uint256 amountProcessed);

    constructor(address _endpoint, address _oApp, address _remoteCaller, bool _allowPayableLzCompose) {
        endpoint = _endpoint;
        oApp = _oApp;
        remoteCaller = OFTComposeMsgCodec.addressToBytes32(_remoteCaller);
        allowPayableLzCompose = _allowPayableLzCompose;
    }

    /**
        @param _oApp The address initiating the composition, typically the OApp where the lzReceive was called.
        @param _guid The unique identifier for the corresponding LayerZero src/dst tx.
        @param _message The composed message payload in bytes.
        @param _lzExecutor The address of the executor for the composed message.
        @param _extraData Additional arbitrary data in bytes passed by the entity who executes the lzCompose.
     */
    function lzCompose(
        address _oApp,
        bytes32 _guid,
        bytes calldata _message,
        address _lzExecutor,
        bytes calldata _extraData
    ) external payable {
        require(msg.sender == endpoint, "DFM: Only lzEndpoint");
        require(_oApp == oApp, "DFM: Incorrect oApp");
        require(OFTComposeMsgCodec.composeFrom(_message) == remoteCaller, "DFM: Incorrect remoteCaller");
        if (!allowPayableLzCompose) require(msg.value == 0, "DFM: msg.value > 0");

        uint256 distributed = _notifyNewFees(OFTComposeMsgCodec.amountLD(_message));

        emit NotifyNewFees(distributed);
    }

    function _notifyNewFees(uint256 received) internal virtual returns (uint256 distributed);
}
