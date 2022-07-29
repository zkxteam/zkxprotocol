// SPDX-License-Identifier: Apache-2.0.
pragma solidity 0.8.14;

import "../IStarknetCore.sol";

contract StarknetCoreMock is IStarknetCore {
    mapping(bytes32 => uint256) public l2ToL1Messages;
    mapping(bytes32 => uint256) public l1ToL2Messages;
    mapping(bytes32 => uint256) public l1ToL2MessageCancellations;

    /* IStarknetCore public */

    uint256 public invokedSendMessageToL2Count = 0;

    function sendMessageToL2(
        uint256 toAddress,
        uint256 selector,
        uint256[] calldata payload
    ) external override returns (bytes32) {
        invokedSendMessageToL2Count += 1;
        bytes32 msgHash = keccak256(
            abi.encodePacked(
                toAddress,
                uint256(uint160(msg.sender)),
                selector,
                payload.length,
                payload
            )
        );
        l1ToL2Messages[msgHash] += 1;
        return msgHash;
    }

    uint256 public invokedConsumeMessageFromL2Count = 0;

    function consumeMessageFromL2(
        uint256 fromAddress,
        uint256[] calldata payload
    ) external override returns (bytes32) {
        invokedConsumeMessageFromL2Count += 1;
        bytes32 msgHash = keccak256(
            abi.encodePacked(
                fromAddress,
                uint256(uint160(msg.sender)),
                payload.length,
                payload
            )
        );
        require(l2ToL1Messages[msgHash] > 0, "INVALID_MESSAGE_TO_CONSUME");
        l2ToL1Messages[msgHash] -= 1;
        return msgHash;
    }

    uint256 public invokedCancelMessageToL2Count = 0;

    function messageCancellationDelay() public pure returns (uint256) {
        return 5 minutes;
    }

    function startL1ToL2MessageCancellation(
        uint256 toAddress,
        uint256 selector,
        uint256[] calldata payload,
        uint256 nonce
    ) external override {
        bytes32 msgHash = keccak256(
            abi.encodePacked(
                toAddress,
                uint256(uint160(msg.sender)),
                selector,
                payload.length,
                payload
            )
        );
        uint256 msgCount = l1ToL2Messages[msgHash];
        require(msgCount > 0, "NO_MESSAGE_TO_CANCEL");
        l1ToL2MessageCancellations[msgHash] = block.timestamp;
        invokedCancelMessageToL2Count += 1;
    }

    function cancelL1ToL2Message(
        uint256 toAddress,
        uint256 selector,
        uint256[] calldata payload,
        uint256 nonce
    ) external override {
        bytes32 msgHash = keccak256(
            abi.encodePacked(
                toAddress,
                uint256(uint160(msg.sender)),
                selector,
                payload.length,
                payload
            )
        );
        uint256 msgCount = l1ToL2Messages[msgHash];
        require(msgCount > 0, "NO_MESSAGE_TO_CANCEL");

        uint256 requestTime = l1ToL2MessageCancellations[msgHash];
        require(requestTime != 0, "MESSAGE_CANCELLATION_NOT_REQUESTED");

        uint256 cancelAllowedTime = requestTime + messageCancellationDelay();
        require(
            block.timestamp >= cancelAllowedTime,
            "MESSAGE_CANCELLATION_NOT_ALLOWED_YET"
        );

        l1ToL2Messages[msgHash] = msgCount - 1;
    }

    /* Mock setup */

    function addL2ToL1Message(
        uint256 fromAddress,
        address sender,
        uint256[] calldata payload
    ) external returns (bytes32) {
        bytes32 msgHash = keccak256(
            abi.encodePacked(
                fromAddress,
                uint256(uint160(sender)),
                payload.length,
                payload
            )
        );
        l2ToL1Messages[msgHash] += 1;
        return msgHash;
    }

    function resetCounters() external {
        invokedSendMessageToL2Count = 0;
        invokedConsumeMessageFromL2Count = 0;
    }
}
