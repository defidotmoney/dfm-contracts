// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { ILayerZeroComposer } from "@layerzerolabs/lz-evm-protocol-v2/contracts/interfaces/ILayerZeroComposer.sol";
import { MessagingFee, SendParam } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/interfaces/IOFT.sol";
import { IBridgeToken } from "../interfaces/IBridgeToken.sol";
import { SystemStart } from "../base/dependencies/SystemStart.sol";
import { LocalReceiverBase } from "./dependencies/LocalReceiverBase.sol";
import { TokenRecovery } from "./dependencies/TokenRecovery.sol";

/**
    @title LzCompose Fee Forwarder
    @author defidotmoney
    @dev Bridges received stablecoin fees to another chain and then notifies the
         receiver via a LayerZero composed message. The receiver must inherit
         the `LzComposeReceiverBase` abstract base.
 */
contract LzComposeForwarder is LocalReceiverBase, TokenRecovery, SystemStart {
    uint256 constant MIN_AMOUNT = 100 * 1e18;

    IBridgeToken public immutable stableCoin;
    uint32 public immutable thisId;
    uint256 public immutable bridgeEpochFrequency;

    ILayerZeroComposer public remoteReceiver;
    uint32 public remoteEid;
    uint64 public gasLimit;

    event ReceiverSet(ILayerZeroComposer receiver, uint32 eid);
    event GasLimitSet(uint64 gasLimit);

    /**
        @notice Contract constructor
        @param _receiver Address of the contract on the remote chain that receives
                         the bridged tokens. Must inherit `LzComposeReceiverBase`.
                         Can be left unset at deployment, but must be configured via
                         `setRemoteReceiver` for the contract to function correctly.
        @param _bridgeFrequency Bridging happens once in this many epochs. To
                                bridge tokens every epoch, set as 1.
     */
    constructor(
        address _core,
        IBridgeToken _stable,
        address _feeAggregator,
        ILayerZeroComposer _receiver,
        uint32 _remoteEid,
        uint64 _gasLimit,
        uint256 _bridgeFrequency
    ) LocalReceiverBase(_feeAggregator) TokenRecovery(_core) SystemStart(_core) {
        require(_bridgeFrequency != 0, "DFM: _bridgeFrequency == 0");

        stableCoin = _stable;
        thisId = _stable.thisId();
        bridgeEpochFrequency = _bridgeFrequency;

        if (address(_receiver) != address(0)) _setReceiver(_receiver, _remoteEid);
        _setGasLimit(_gasLimit);
    }

    // --- external view functions ---

    function quoteNotifyNewFees(uint256 received) external view override returns (uint256 nativeFee) {
        if (getWeek() % bridgeEpochFrequency == 0) {
            uint256 amount = stableCoin.balanceOf(address(this)) + received;
            if (amount >= MIN_AMOUNT) {
                SendParam memory params = _getSendParams(amount);
                return stableCoin.quoteSend(params, false).nativeFee;
            }
        }
        return 0;
    }

    // --- guarded external functions ---

    function _notifyNewFees(uint256) internal override returns (uint256 distributed) {
        if (getWeek() % bridgeEpochFrequency == 0) {
            uint256 amount = stableCoin.balanceOf(address(this));
            if (amount >= MIN_AMOUNT) {
                SendParam memory params = _getSendParams(amount);
                MessagingFee memory fee = MessagingFee(address(this).balance, 0);
                stableCoin.send{ value: address(this).balance }(params, fee, msg.sender);

                return amount;
            }
        }
    }

    function setRemoteReceiver(ILayerZeroComposer receiver, uint32 eid) external onlyOwner {
        _setReceiver(receiver, eid);
    }

    function setGasLimit(uint64 gas) external onlyOwner {
        _setGasLimit(gas);
    }

    // --- internal functions ---

    function _getSendParams(uint256 amount) internal view returns (SendParam memory params) {
        bytes memory baseOptions = stableCoin.defaultOptions();
        return
            SendParam({
                dstEid: remoteEid,
                to: bytes32(uint256(uint160(address(remoteReceiver)))),
                amountLD: amount,
                minAmountLD: 0,
                extraOptions: abi.encodePacked(baseOptions, hex"010013030000", uint128(gasLimit)),
                composeMsg: hex"00",
                oftCmd: bytes("")
            });
    }

    function _setReceiver(ILayerZeroComposer receiver, uint32 eid) internal {
        require(address(receiver) != address(0), "DFM: Empty receiver");
        require(stableCoin.peers(eid) != bytes32(0), "DFM: Receiver peer unset");
        remoteReceiver = receiver;
        remoteEid = eid;

        emit ReceiverSet(receiver, eid);
    }

    function _setGasLimit(uint64 gas) internal {
        require(gas >= 50000, "DFM: gasLimit too low");
        gasLimit = gas;

        emit GasLimitSet(gas);
    }
}
