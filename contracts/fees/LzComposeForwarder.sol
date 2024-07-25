// SPDX-License-Identifier: MIT

pragma solidity 0.8.25;

import { MessagingFee, SendParam } from "@layerzerolabs/lz-evm-oapp-v2/contracts/oft/interfaces/IOFT.sol";
import { IBridgeToken } from "../interfaces/IBridgeToken.sol";
import { SystemStart } from "../base/dependencies/SystemStart.sol";
import { IFeeReceiver } from "../interfaces/IFeeReceiver.sol";
import { IFeeReceiverLzCompose } from "../interfaces/IFeeReceiverLzCompose.sol";
import { TokenRecovery } from "./dependencies/TokenRecovery.sol";

/**
    @title LzCompose Fee Forwarder
    @author defidotmoney
    @dev Bridges received stablecoin fees to another chain and then notifies the
         receiver via a LayerZero composed message. The receiver must implement
         the `IFeeReceiverLzCompose` interface.
 */
contract LzComposeForwarder is TokenRecovery, SystemStart, IFeeReceiver {
    uint256 constant MIN_AMOUNT = 100 * 1e18;

    IBridgeToken public immutable stableCoin;
    address public immutable feeAggregator;
    uint32 public immutable thisId;
    uint256 public immutable bridgeEpochFrequency;

    IFeeReceiverLzCompose public remoteReceiver;
    uint32 public remoteEid;
    uint64 public gasLimit;

    event ReceiverSet(IFeeReceiverLzCompose receiver, uint32 eid);
    event GasLimitSet(uint64 gasLimit);

    /**
        @notice Contract constructor
        @param _bridgeFrequency Bridging happens once in this many epochs. To
                                bridge tokens every epoch, set as 1.
     */
    constructor(
        address _core,
        IBridgeToken _stable,
        address _feeAggregator,
        IFeeReceiverLzCompose _receiver,
        uint32 _remoteEid,
        uint64 _gasLimit,
        uint256 _bridgeFrequency
    ) TokenRecovery(_core) SystemStart(_core) {
        require(_bridgeFrequency != 0, "DFM: _bridgeFrequency == 0");

        stableCoin = _stable;
        feeAggregator = _feeAggregator;
        thisId = _stable.thisId();
        bridgeEpochFrequency = _bridgeFrequency;

        _setReceiver(_receiver, _remoteEid);
        _setGasLimit(_gasLimit);
    }

    // --- external view functions ---

    function quoteNotifyNewFees(uint256) external view returns (uint256 nativeFee) {
        if (getWeek() % bridgeEpochFrequency == 0) {
            uint256 amount = stableCoin.balanceOf(address(this));
            if (amount >= MIN_AMOUNT) {
                SendParam memory params = _getSendParams(amount);
                return stableCoin.quoteSend(params, false).nativeFee;
            }
        }
        return 0;
    }

    // --- guarded external functions ---

    function notifyNewFees(uint256) external payable {
        require(msg.sender == feeAggregator, "DFM: Only feeAggregator");
        if (getWeek() % bridgeEpochFrequency == 0) {
            uint256 amount = stableCoin.balanceOf(address(this));
            if (amount >= MIN_AMOUNT) {
                SendParam memory params = _getSendParams(amount);
                MessagingFee memory fee = MessagingFee(address(this).balance, 0);
                stableCoin.send{ value: address(this).balance }(params, fee, msg.sender);

                emit NotifyNewFees(amount);
                return;
            }
        }

        if (msg.value != 0) {
            (bool success, ) = msg.sender.call{ value: msg.value }("");
            require(success, "DFM: Gas refund transfer failed");
        }
        emit NotifyNewFees(0);
    }

    function setRemoteReceiver(IFeeReceiverLzCompose receiver, uint32 eid) external onlyOwner {
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

    function _setReceiver(IFeeReceiverLzCompose receiver, uint32 eid) internal {
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
