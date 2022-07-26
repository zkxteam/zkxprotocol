// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.8.7;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "./IStarknetCore.sol";
import "./Constants.sol";

// Contract for L1 <-> L2 interaction between an L2 contracts and this L1 ZKX contract.
contract L1ZKXContract is AccessControl {

    event LogDeposit(
        address sender,
        uint256 amount_,
        uint256 collateralId_,
        uint256 l2Recipient
    );

    event LogWithdrawal(
        address recipient,
        uint256 ticker_,
        uint256 amount_,
        uint256 requestId_
    );

    event LogAssetListUpdated(uint256 ticker_, uint256 collateralId_);

    event LogAssetRemovedFromList(uint256 ticker_, uint256 collateralId_);

    event LogTokenContractAddressUpdated(
        uint256 ticker_,
        address tokenContractAddresses_
    );

    using SafeMath for uint256;

    // The StarkNet core contract.
    IStarknetCore public starknetCore;

    // Maps ticker to the token contract addresses
    mapping(uint256 => address) public tokenContractAddress;

    // Maps ticker with the asset ID
    mapping(uint256 => uint256) public assetID;

    // List of assets
    uint256[] public assetList;

    // Asset Contract address
    uint256 public assetContractAddress;

    // Withdrawal Request Contract Address
    uint256 public withdrawalRequestContractAddress;

    /**
      Modifier to verify valid L2 address.
    */
    modifier isValidL2Address(uint256 l2Address_) {
        require(l2Address_ != 0 && l2Address_ < FIELD_PRIME, "L2_ADDRESS_OUT_OF_RANGE");
        _;
    }

    /**
      Initializes the contract state.
    */
    constructor(
        IStarknetCore starknetCore_,
        uint256 assetContractAddress_,
        uint256 withdrawalRequestContractAddress_
    ) {
        starknetCore = starknetCore_;
        assetContractAddress = assetContractAddress_;
        withdrawalRequestContractAddress = withdrawalRequestContractAddress_;
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    /**
     * @dev function to update asset list in L1
     * @param ticker_ - felt representation of the ticker
     * @param assetId_ - Id of the asset created
     **/
    function updateAssetListInL1(uint256 ticker_, uint256 assetId_)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        // Construct the update asset list message's payload.
        uint256[] memory payload = new uint256[](3);
        payload[0] = ADD_ASSET_INDEX;
        payload[1] = ticker_;
        payload[2] = assetId_;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(assetContractAddress, payload);

        // Update the asset list
        assetID[ticker_] = assetId_;
        assetList.push(ticker_);
        emit LogAssetListUpdated(ticker_, assetId_);
    }

    /**
     * @dev function to remove asset from list in L1
     * @param ticker_ - felt representation of the ticker
     * @param assetId_ - Id of the asset to be removed
     **/
    function removeAssetFromList(uint256 ticker_, uint256 assetId_)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        // Construct the remove asset message's payload.
        uint256[] memory payload = new uint256[](3);
        payload[0] = REMOVE_ASSET_INDEX;
        payload[1] = ticker_;
        payload[2] = assetId_;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(assetContractAddress, payload);

        // Update the asset mapping
        assetID[ticker_] = 0;

        // Remove the asset from the asset list
        uint256 index;
        for (uint256 i = 0; i < assetList.length; i++) {
            if (assetList[i] == ticker_) {
                index = i;
                break;
            }
        }
        assetList[index] = assetList[assetList.length - 1];
        assetList.pop();

        emit LogAssetRemovedFromList(ticker_, assetId_);
    }

    /**
     * @dev function to get the list of available assets
     **/
    function getAssetList() external view returns (uint256[] memory) {
        return assetList;
    }

    /**
     * @dev function to set token contract address
     * @param ticker_ - felt representation of the ticker
     * @param tokenContractAddress_ - address of the token contract
     **/
    function setTokenContractAddress(
        uint256 ticker_,
        address tokenContractAddress_
    ) 
        external 
        onlyRole(DEFAULT_ADMIN_ROLE) 
    {
        // Update token contract address
        tokenContractAddress[ticker_] = tokenContractAddress_;
        emit LogTokenContractAddressUpdated(ticker_, tokenContractAddress_);
    }

    /**
     * @dev function to set asset contract address
     * @param assetContractAddress_ - address of the asset contract
     **/
    function setAssetContractAddress(uint256 assetContractAddress_)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        assetContractAddress = assetContractAddress_;
    }

    /**
     * @dev function to set withdrawal request contract address
     * @param withdrawalRequestAddress_ - address of withdrawal request contract
     **/
    function setWithdrawalRequestAddress(uint256 withdrawalRequestAddress_)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        withdrawalRequestContractAddress = withdrawalRequestAddress_;
    }

    /**
     * @dev function to deposit funds to L2 Account contract
     * @param userL1Address_ - Users L1 wallet address
     * @param collateralId_ - ID of the collateral
     * @param amount_ - The amount of tokens to be deposited
     **/
    function depositToL2(
        uint256 userL1Address_,
        uint256 userL2Address_,
        uint256 collateralId_,
        uint256 amount_
    ) private {

        // Construct the deposit message's payload.
        uint256[] memory depositPayload = new uint256[](3);
        depositPayload[0] = userL1Address_;
        depositPayload[1] = amount_;
        depositPayload[2] = collateralId_;

        // Send the message to the StarkNet core contract.
        starknetCore.sendMessageToL2(
            userL2Address_,
            DEPOSIT_SELECTOR,
            depositPayload
        );

        emit LogDeposit(
            msg.sender,
            amount_,
            collateralId_,
            userL2Address_
        );
    }

    /**
     * @dev function to deposit funds to L1ZKX contract
     * @param userL2Address_ - The L2 account address of the user
     * @param ticker_ - felt representation of the ticker
     * @param amount_ - The amount of collateral to be deposited
     **/
    function depositToL1(
        uint256 userL2Address_,
        uint256 ticker_,
        uint256 amount_
    ) 
        external 
        isValidL2Address(userL2Address_) 
    {   

        // Transfer tokens
        uint256 senderAsUint256 = uint256(uint160(address(msg.sender)));
        address tokenContract = tokenContractAddress[ticker_];
        require(tokenContract != address(0), "Unregistered ticker");
        IERC20 Token = IERC20(tokenContract);
        address zkxAddress = address(this);
        uint256 zkxBalanceBefore = Token.balanceOf(zkxAddress);
        Token.transferFrom(msg.sender, zkxAddress, amount_);
        uint256 zkxBalanceAfter = Token.balanceOf(zkxAddress);
        require(zkxBalanceAfter >= zkxBalanceBefore + amount_, "Invalid transfer amount");

        // Submit deposit
        uint256 collateralId = assetID[ticker_];
        depositToL2(
            senderAsUint256,
            userL2Address_,
            collateralId,
            amount_
        );
    }

    /**
     * @dev function to deposit ETH to L1ZKX contract
     * @param userL2Address_ - The L2 account address of the user
     **/
    function depositEthToL1(uint256 userL2Address_) 
        payable 
        external 
        isValidL2Address(userL2Address_) 
    {
        // If not yet set, store L2 address linked to sender's L1 address
        uint256 senderAsUint256 = uint256(uint160(address(msg.sender)));
        if (l2ContractAddress[senderAsUint256] == 0) {
            l2ContractAddress[senderAsUint256] = userL2Address_;
        }

        // Submit deposit
        uint256 collateralId = assetID[ETH_TICKER];
        depositToL2(
            senderAsUint256,
            userL2Address_,
            collateralId,
            msg.value
        );
    }

    /**
     * @dev function to withdraw funds from an L2 Account contract
     * @param userL2Address_ - Users L2 Account address
     * @param ticker_ - felt representation of the ticker
     * @param amount_ - The amount of tokens to be withdrawn
     * @param requestId_ - ID of the withdrawal request
     **/
    function withdraw(
        uint256 userL2Address_,
        uint256 ticker_,
        uint256 amount_,
        uint256 requestId_
    ) external {

        // Construct withdrawal message payload.
        uint256[] memory withdrawal_payload = new uint256[](5);
        withdrawal_payload[0] = WITHDRAWAL_INDEX;
        withdrawal_payload[1] = userL1Address_;
        withdrawal_payload[2] = ticker_;
        withdrawal_payload[3] = amount_;
        withdrawal_payload[4] = requestId_;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(userL2Address_, withdrawal_payload);

        address tokenContract = tokenContractAddress[ticker_];
        IERC20(tokenContract).transfer(msg.sender, amount_);

        // Construct update withdrawal request message payload.
        uint256[] memory updateWithdrawalRequestPayload = new uint256[](2);
        updateWithdrawalRequestPayload[0] = userL2Address_;
        updateWithdrawalRequestPayload[1] = requestId_;

        // Send the message to the StarkNet core contract.
        starknetCore.sendMessageToL2(
            withdrawalRequestContractAddress,
            UPDATE_WITHDRAWAL_REQUEST_SELECTOR,
            updateWithdrawalRequestPayload
        );

        emit LogWithdrawal(msg.sender, ticker_, amount_, requestId_);
    }

    /**
     * @dev function to withdraw funds from an L2 Account contract
     * @param userL2Address_ - Users L2 Account address
     * @param amount_ - The amount of tokens to be withdrawn
     * @param requestId_ - ID of the withdrawal request
     **/
    function withdrawEth(
        uint256 userL2Address_,
        uint256 amount_,
        uint256 requestId_
    ) external {

        // Construct withdrawal message payload.
        uint256[] memory withdrawal_payload = new uint256[](5);
        withdrawal_payload[0] = WITHDRAWAL_INDEX;
        withdrawal_payload[1] = uint256(uint160(userL1Address_));
        withdrawal_payload[2] = ETH_TICKER;
        withdrawal_payload[3] = amount_;
        withdrawal_payload[4] = requestId_;

        require(amount_ <= address(this).balance, "ETH to be transferred is more than the balance");
        payable(msg.sender).transfer(amount_);

        // Construct update withdrawal request message payload.
        uint256[] memory updateWithdrawalRequestPayload = new uint256[](2);
        updateWithdrawalRequestPayload[0] = userL2Address_;
        updateWithdrawalRequestPayload[1] = requestId_;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(userL2Address_, withdrawal_payload);

        // Send the message to the StarkNet core contract.
        starknetCore.sendMessageToL2(
            withdrawalRequestContractAddress,
            UPDATE_WITHDRAWAL_REQUEST_SELECTOR,
            updateWithdrawalRequestPayload
        );

        emit LogWithdrawal(msg.sender, ETH_TICKER, amount_, requestId_);
    }

     /**
     * @dev function to transfer funds from this contract to another address
     * @param recipient_ - address of the recipient
     * @param amount_ - amount that needs to be transferred
     * @param tokenAddress_ - address of the token contract
     **/
    function transferFunds(address recipient_, uint256 amount_, address tokenAddress_)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        uint256 balance = IERC20(tokenAddress_).balanceOf(address(this));
        require(amount_ <= balance, "Not enough ERC-20 tokens to withdraw");
        IERC20(tokenAddress_).transfer(recipient_, amount_);
    }

    /**
     * @dev function to transfer funds from this contract to another address
     * @param recipient_ - address of the recipient
     * @param amount_ - amount that needs to be transferred
     **/
    function transferEth(address payable recipient_, uint256 amount_)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        require(amount_ <= address(this).balance, "ETH to be transferred is more than the balance");
        recipient_.transfer(amount_);
    }
}
