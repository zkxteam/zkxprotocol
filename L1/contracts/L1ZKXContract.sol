// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.8.2;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "./IStarknetCore.sol";


/**
  Contract for L1 <-> L2 interaction between an L2 StarkNet Account contract and this
  L1 ZKX contract.
*/
contract L1ZKXContract is AccessControl{

    event LogDeposit(address sender, uint256 amount, uint256 collateralId, uint256 l2Recipient);
    event LogWithdrawal(address recipient, uint256 amount);
    event LogAssetListUpdated(uint256 ticker, uint256 collateralId);
    event LogAssetContractAddressUpdated(uint256 ticker, address assetContractAddresses_);

    using SafeMath for uint256;

    // The StarkNet core contract.
    IStarknetCore starknetCore;

    // Maps asset with the asset contract addresses
    mapping(uint256 => address) public assetContractAddress;

    // Maps ticker with the asset ID
    mapping(uint256 => uint256) public assetID;

    // Maps asset id with the amount of collateral available 
    //mapping(uint256 => uint256) public collateralBalance;

    // Maps the user address to the asset balance mapping
    mapping(uint256 => mapping(uint256 => uint256)) public userBalance;

    // Maps L1 metamask account address to the l2 account contract address
    mapping(uint256 => uint256) public l2ContractAddress;

     // List of assets
    uint256[] public assetList;
    
    uint256 constant MESSAGE_WITHDRAW = 0;
    uint256 constant ADD_ASSET = 1;
    address admin_address = 0x463f2125e3bc6BA05eF5DfC4A7979Cb5B004E1ac;


    // The selector of the "deposit" l1_handler.
    uint256 constant DEPOSIT_SELECTOR =
        352040181584456735608515580760888541466059565068553383579463728554843487745;

    // Asset Contract address
    uint256 zkxAssetContractAddress = 
        0x0322f2b0aa7c053c8af5260ac6411aaae4cab234b4bb77c06d92e959359a37a8;

    uint256 constant FIELD_PRIME =
        0x800000000000011000000000000000000000000000000000000000000000001;

    /**
      Initializes the contract state.
    */
    constructor(IStarknetCore starknetCore_) {
        starknetCore = starknetCore_;
        _setupRole(DEFAULT_ADMIN_ROLE, admin_address);
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
     * @dev function to get the L2 contract address for the corresponding L1 account address
     **/
    function getL2ContractAddress(uint256 user) public view returns (uint256) {
        return l2ContractAddress[user];
    }

    /**
     * @dev function to update asset list in L1
     * @param ticker - The asset that needs to be added to the list
     * @param  assetId - Id of the asset created
     **/
    function updateAssetListInL1 (uint256 ticker,
        uint256 assetId) public onlyRole(DEFAULT_ADMIN_ROLE) {

        // Construct the withdrawal message's payload.
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
     * @dev function to get the list of available assets
     **/
    function getAssetList() public view returns (uint256[] memory) {
        return assetList;
    }

     /**
     * @dev function to set asset contract address
     * @param ticker - The asset that needs to be added to the list
     * @param  assetContractAddress_ - address of the asset contract
     **/
    function setAssetContractAddress (uint256 ticker,
        address assetContractAddress_) public onlyRole(DEFAULT_ADMIN_ROLE) {

        // Update the asset list
        assetContractAddress[ticker] = assetContractAddress_;
        emit LogAssetContractAddressUpdated(ticker, assetContractAddress_);
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
        uint256 l2AccountAddress = getL2ContractAddress(user);

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

        address tokenContract = assetContractAddress[ticker];
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

        uint256 l2Recipient = getL2ContractAddress(user);

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

        address tokenContract = assetContractAddress[ticker];
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