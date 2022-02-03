// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.8.2;

import "./IStarknetCore.sol";
import "./ZKXToken.sol";

/**
  Contract for L1 <-> L2 interaction between an L2 StarkNet Account contract and this
  L1 ZKX contract.
*/
contract L1ZKXContract {

    event LogDeposit(address sender, uint256 amount, uint256 l2Recipient);
    event LogWithdrawal(address recipient, uint256 amount);

    // The StarkNet core contract.
    IStarknetCore starknetCore;

    // The ZKXToken contract
    ZKXToken zkxToken;

    mapping(uint256 => uint256) public userBalances;
    
    uint256 constant MESSAGE_WITHDRAW = 0;

    // The selector of the "deposit" l1_handler.
    uint256 constant DEPOSIT_SELECTOR =
        352040181584456735608515580760888541466059565068553383579463728554843487745;

    uint256 constant FIELD_PRIME =
        0x800000000000011000000000000000000000000000000000000000000000001;

    /**
      Initializes the contract state.
    */
    constructor(IStarknetCore starknetCore_, address ZKXTokenAddress_) {
        starknetCore = starknetCore_;
        zkxToken = ZKXToken(ZKXTokenAddress_);
    }

    /**
      Modifier to verify valid L2 address.
    */
    modifier isValidL2Address(uint256 l2Address) {
        require(l2Address != 0, "L2_ADDRESS_OUT_OF_RANGE");
        require(l2Address < FIELD_PRIME, "L2_ADDRESS_OUT_OF_RANGE");
        _;
    }

    /**
     * @dev function to withdraw funds from an L2 Account contract
     * @param  l2ContractAddress - The L2 address from which funds should be taken 
     * @param amount - The amount of tokens to be withdrawn
     **/
    function withdraw(
        uint256 l2ContractAddress,
        uint256 amount
    ) external {

        uint256 user = uint256(uint160(address(msg.sender)));
        // Construct the withdrawal message's payload.
        uint256[] memory payload = new uint256[](3);
        payload[0] = MESSAGE_WITHDRAW;
        payload[1] = user;
        payload[2] = amount;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(l2ContractAddress, payload);

        // Update the User balance.
        //userBalances[user] += amount;
        zkxToken.transfer(address(uint160(user)), amount);
        emit LogWithdrawal(address(uint160(user)), amount);
    }

    /**
     * @dev function to deposit funds to L2 Account contract
     * @param user - Users Metamask account address
     * @param  l2Recipient - The L2 address to which the deposited funds should be sent to
     * @param amount - The amount of tokens to be deposited
     **/
    function depositToL2(
        uint256 user,
        uint256 amount,
        uint256 l2Recipient
    ) internal isValidL2Address(l2Recipient){
        
        require(amount <= userBalances[user], "The user's balance is not large enough.");

        // Update the User balance.
        userBalances[user] -= amount;

        // Construct the deposit message's payload.
        uint256[] memory payload = new uint256[](2);
        payload[0] = user;
        payload[1] = amount;

        // Send the message to the StarkNet core contract.
        starknetCore.sendMessageToL2(l2Recipient, DEPOSIT_SELECTOR, payload);
        emit LogDeposit(address(uint160(user)), amount, l2Recipient);
    }

    /**
     * @dev function to deposit funds to L1ZKX contract
     * @param  l2RecipientAddress- The L2 address to which the deposited funds should be sent to
     * @param amount - The amount of tokens to be deposited
     **/
    function depositToL1(uint256 amount, uint256 l2RecipientAddress) public isValidL2Address(l2RecipientAddress){
        zkxToken.transferFrom(msg.sender, address(this), amount);
        // Update the User balance.
        userBalances[uint256(uint160(address(msg.sender)))] += amount;
        depositToL2(uint256(uint160(address(msg.sender))), amount, l2RecipientAddress);
    }
}