// SPDX-License-Identifier: Apache-2.0.
pragma solidity 0.8.14;

import "../IStarknetCore.sol";

contract StarknetCoreMock is IStarknetCore {

    mapping(bytes32 => uint256) public l2ToL1Messages;

    /* IStarknetCore public */

    uint public invokedSendMessageToL2Count = 0;
    
    function sendMessageToL2(
        uint256 to_address,
        uint256 selector,
        uint256[] calldata payload
    )
        override
        external 
        returns (bytes32)
    {
        invokedSendMessageToL2Count += 1;
        /* Do nothing */
        return bytes32(0);
    }

    uint public invokedConsumeMessageFromL2Count = 0;
    
    function consumeMessageFromL2(
        uint256 fromAddress, 
        uint256[] calldata payload
    )
        override
        external
        returns (bytes32) 
    {
        invokedConsumeMessageFromL2Count += 1;
        bytes32 msgHash = keccak256(
            abi.encodePacked(fromAddress, uint256(uint160(msg.sender)), payload.length, payload)
        );
        require(l2ToL1Messages[msgHash] > 0, "INVALID_MESSAGE_TO_CONSUME");
        l2ToL1Messages[msgHash] -= 1;
        return msgHash;
    }

    /* Mock setup */

    function addL2ToL1Message(
        uint256 fromAddress,
        address sender,
        uint256[] calldata payload
    ) 
        external 
        returns (bytes32) 
    {  
        bytes32 msgHash = keccak256(
            abi.encodePacked(fromAddress, uint256(uint160(sender)), payload.length, payload)
        );
        l2ToL1Messages[msgHash] += 1;
        return msgHash;
    }

    function resetCounters() external {
        invokedSendMessageToL2Count = 0;
        invokedConsumeMessageFromL2Count = 0;
    }
}
