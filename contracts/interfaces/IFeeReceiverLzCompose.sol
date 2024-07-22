// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { ILayerZeroComposer } from "@layerzerolabs/lz-evm-protocol-v2/contracts/interfaces/ILayerZeroComposer.sol";

/**
    @dev Contracts that receive stablecoin fees through a bridging action initiated
         by `LzComposeForwarder` must implement this interface.
 */
interface IFeeReceiverLzCompose is ILayerZeroComposer {
    /**
        @notice Receive a composed LayerZero message from an OApp.
        @dev Implementations should verify that:
             * `_oApp` is the stablecoin
             * `msg.sender` is the local LayerZero endpoint
             It is also important that the logic has no expectation that it is only
             executed once per epoch as a result of a call to `LzComposeForwarder` on
             another chain. Anyone can interact with stableCoin to send a composed message
             to this contract at any time.
     */
    function lzCompose(
        address _oApp,
        bytes32 _guid,
        bytes calldata _message,
        address _lzExecutor,
        bytes calldata _extraData
    ) external payable;
}
