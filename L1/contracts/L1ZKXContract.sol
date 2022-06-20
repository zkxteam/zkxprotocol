// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.8.2;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "./IStarknetCore.sol";


/**
  Contract for L1 <-> L2 interaction between an L2 contracts and this
  L1 ZKX contract.
*/
contract L1ZKXContract is AccessControl{

    event LogDeposit(address sender, uint256 amount, uint256 collateralId, uint256 l2Recipient);
    event LogWithdrawal(address recipient, uint256 amount);
    event LogAssetListUpdated(uint256 ticker, uint256 collateralId);
    event LogAssetRemovedFromList(uint256 ticker, uint256 collateralId);
    event LogTokenContractAddressUpdated(uint256 ticker, address tokenContractAddresses_);

    using SafeMath for uint256;

    // The StarkNet core contract.
    IStarknetCore starknetCore;

    // Maps token with the token contract addresses
    mapping(uint256 => address) public tokenContractAddress;

    // Maps ticker with the asset ID
    mapping(uint256 => uint256) public assetID;

    // Maps the user address to the corresponding asset balance 
    mapping(uint256 => mapping(uint256 => uint256)) public userBalance;

    // Maps L1 metamask account address to the l2 account contract address
    mapping(uint256 => uint256) public l2ContractAddress;

     // List of assets
    uint256[] public assetList;
    
    uint256 constant MESSAGE_WITHDRAW = 0;
    uint256 constant ADD_ASSET = 1;
    uint256 constant REMOVE_ASSET = 2;

    // The selector of the "deposit" l1_handler.
    uint256 constant DEPOSIT_SELECTOR =
        352040181584456735608515580760888541466059565068553383579463728554843487745;

    // Asset Contract address
    uint256 public zkxAssetContractAddress;

    uint256 constant FIELD_PRIME =
        0x800000000000011000000000000000000000000000000000000000000000001;

    /**
      Modifier to verify valid L2 address.
    */
    modifier isValidL2Address(uint256 l2Address) {
        require(l2Address != 0, "L2_ADDRESS_OUT_OF_RANGE");
        require(l2Address < FIELD_PRIME, "L2_ADDRESS_OUT_OF_RANGE");
        _;
    }

    /**
      Initializes the contract state.
    */
    constructor(IStarknetCore starknetCore_, uint256 zkxAssetContractAddress_) {
        starknetCore = starknetCore_;
        zkxAssetContractAddress = zkxAssetContractAddress_;
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    /**
     * @dev function to update asset list in L1
     * @param ticker - The asset that needs to be added to the list
     * @param  assetId - Id of the asset created
     **/
    function updateAssetListInL1 (uint256 ticker,
        uint256 assetId) public onlyRole(DEFAULT_ADMIN_ROLE) {

        // Construct the update asset list message's payload.
        uint256[] memory payload = new uint256[](3);
        payload[0] = ADD_ASSET;
        payload[1] = ticker;
        payload[2] = assetId;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(zkxAssetContractAddress, payload);

        // Update the asset list
        assetID[ticker] = assetId;
        assetList.push(ticker);
        emit LogAssetListUpdated(ticker, assetId);
    }

    /**
     * @dev function to remove asset from list in L1
     * @param ticker - The asset that needs to be removed from the list
     * @param  assetId - Id of the asset to be removed
     **/
    function removeAssetFromList (uint256 ticker,
        uint256 assetId) public onlyRole(DEFAULT_ADMIN_ROLE) {

        // Construct the remove asset message's payload.
        uint256[] memory payload = new uint256[](3);
        payload[0] = REMOVE_ASSET;
        payload[1] = ticker;
        payload[2] = assetId;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(zkxAssetContractAddress, payload);

        // Update the asset mapping
        assetID[ticker] = 0;

        // Remove the asset from the asset list
        uint256 index;
        for (uint i = 0; i<assetList.length; i++){
            if (assetList[i] == ticker) {
                index = i;
                break;
            }
        }
        assetList[index] = assetList[assetList.length-1];
        assetList.pop();

        emit LogAssetRemovedFromList(ticker, assetId);
    }

    /**
     * @dev function to get the list of available assets
     **/
    function getAssetList() public view returns (uint256[] memory) {
        return assetList;
    }

     /**
     * @dev function to set asset contract address
     * @param ticker - The asset that needs to be added to the list
     * @param  tokenContractAddress_ - address of the asset contract
     **/
    function setTokenContractAddress (uint256 ticker,
        address tokenContractAddress_) public onlyRole(DEFAULT_ADMIN_ROLE) {

        // Update the asset list
        tokenContractAddress[ticker] = tokenContractAddress_;
        emit LogTokenContractAddressUpdated(ticker, tokenContractAddress_);
    }


    /**
     * @dev function to withdraw funds from an L2 Account contract
     * @param amount - The amount of tokens to be withdrawn
     * @param ticker - the type of asset that needs to be withdrawn
     **/
    function withdraw (
        uint256 amount,
        uint256 ticker
    ) public {
        uint256 user = uint256(uint160(address(msg.sender)));
        uint256 l2AccountAddress = l2ContractAddress[user];

        uint256 collateralId = assetID[ticker];
        // Construct the withdrawal message's payload.
        uint256[] memory payload = new uint256[](4);
        payload[0] = MESSAGE_WITHDRAW;
        payload[1] = user;
        payload[2] = amount;
        payload[3] = collateralId;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(l2AccountAddress, payload);

        address tokenContract = tokenContractAddress[ticker];
        IERC20(tokenContract).transfer(address(uint160(user)), amount);

        emit LogWithdrawal(address(uint160(user)), amount);                                                                                                                                                                                                                                     
    }

    /**
     * @dev function to deposit funds to L2 Account contract
     * @param user - Users Metamask account address
     * @param collateralId - ID of the collateral
     * @param amount - The amount of tokens to be deposited
     **/
    function depositToL2(
        uint256 user,
        uint256 collateralId,
        uint256 amount
    ) internal {
        
        require(amount <= userBalance[user][collateralId], 
                "The user's balance is not large enough.");

        // Update the User balance.
        userBalance[user][collateralId] = userBalance[user][collateralId].sub(amount);

        uint256 l2Recipient = l2ContractAddress[user];

        // Construct the deposit message's payload.
        uint256[] memory payload = new uint256[](3);
        payload[0] = user;
        payload[1] = amount;
        payload[2] = collateralId;

        // Send the message to the StarkNet core contract.
        starknetCore.sendMessageToL2(l2Recipient, DEPOSIT_SELECTOR, payload);
        emit LogDeposit(address(uint160(user)), amount, collateralId, l2Recipient);
    }

    /**
     * @dev function to deposit funds to L1ZKX contract
     * @param l2AccountAddress - The L2 account address for the corresponding L1 account address
     * @param ticker - Type of collateral deposited
     * @param amount - The amount of collateral to be deposited
     **/
    function depositToL1(uint256 l2AccountAddress, uint256 ticker, uint256 amount) public 
        isValidL2Address(l2AccountAddress) {
        
        /**
         * if l2 contract address is not set, then it will be set for the corresponding
         * L1 account address 
         */
        if (l2ContractAddress[uint256(uint160(address(msg.sender)))] == 0) {
            l2ContractAddress[uint256(uint160(address(msg.sender)))] = l2AccountAddress;
        }

        address tokenContract = tokenContractAddress[ticker];
        uint balance = IERC20(tokenContract).balanceOf(msg.sender);
        require(balance >= amount, "User is trying to deposit more than he has");

        IERC20(tokenContract).transferFrom(msg.sender, address(this), amount);
        uint256 collateralId = assetID[ticker];

        // Update the User balance.
        userBalance[uint256(uint160(address(msg.sender)))][collateralId] = 
            userBalance[uint256(uint160(address(msg.sender)))][collateralId].add(amount);
        depositToL2(uint256(uint160(address(msg.sender))), collateralId, amount);
    }
}