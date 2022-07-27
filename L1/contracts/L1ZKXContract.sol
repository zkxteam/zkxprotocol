// SPDX-License-Identifier: Apache-2.0.
pragma solidity 0.8.14;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./IStarknetCore.sol";
import "./Constants.sol";

// Contract for L1 <-> L2 interaction between an L2 contracts and this L1 ZKX contract.
contract L1ZKXContract is Ownable {

    using SafeERC20 for IERC20;

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

    // The StarkNet core contract.
    IStarknetCore public starknetCore;

    // Maps ticker to the token contract addresses
    mapping(uint256 => address) public tokenContractAddress;

    // Maps ticker with the asset ID
    mapping(uint256 => uint256) public assetID;

    // Maps L1 metamask account address to the l2 account contract address
    mapping(uint256 => uint256) public l2ContractAddress;

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
    ) isValidL2Address(assetContractAddress_) isValidL2Address(withdrawalRequestContractAddress_) {
        require(address(starknetCore_) != address(0), "StarknetCore address not provided");
        starknetCore = starknetCore_;
        assetContractAddress = assetContractAddress_;
        withdrawalRequestContractAddress = withdrawalRequestContractAddress_;
    }

    /**
     * @dev function to update asset list in L1
     * @param ticker_ - felt representation of the ticker
     * @param assetId_ - Id of the asset created
     **/
    function updateAssetListInL1(uint256 ticker_, uint256 assetId_)
        external
        onlyOwner
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
        onlyOwner
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
        onlyOwner 
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
        onlyOwner
        isValidL2Address(assetContractAddress_)
    {
        assetContractAddress = assetContractAddress_;
    }

    /**
     * @dev function to set withdrawal request contract address
     * @param withdrawalRequestAddress_ - address of withdrawal request contract
     **/
    function setWithdrawalRequestAddress(uint256 withdrawalRequestAddress_)
        external
        onlyOwner
        isValidL2Address(withdrawalRequestAddress_)
    {
        withdrawalRequestContractAddress = withdrawalRequestAddress_;
    }

    /**
     * @dev function to deposit funds to L2 Account contract
     * @param userL1Address_ - L1 user address
     * @param userL2Address_ - L2 address of user's ZKX account
     * @param collateralId_ - ID of the collateral
     * @param amount_ - The amount of tokens to be deposited
     **/
    function depositToL2(
        uint256 userL1Address_,
        uint256 userL2Address_,
        uint256 collateralId_,
        uint256 amount_
    ) private isValidL2Address(userL2Address_) {

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
        // If not yet set, store L2 address linked to sender's L1 address
        uint256 senderAsUint256 = uint256(uint160(address(msg.sender)));
        if (l2ContractAddress[senderAsUint256] == 0) {
            l2ContractAddress[senderAsUint256] = userL2Address_;
        }

        // Transfer tokens
        address tokenContract = tokenContractAddress[ticker_];
        require(tokenContract != address(0), "Deposit failed: Unregistered ticker");
        IERC20 Token = IERC20(tokenContract);
        address zkxAddress = address(this);
        uint256 zkxBalanceBefore = Token.balanceOf(zkxAddress);
        Token.safeTransferFrom(msg.sender, zkxAddress, amount_);
        uint256 zkxBalanceAfter = Token.balanceOf(zkxAddress);

        require(zkxBalanceAfter >= zkxBalanceBefore + amount_, "Deposit failed: Invalid transfer amount");

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
     * @param userL1Address_ - Users L1 wallet address
     * @param ticker_ - felt representation of the ticker
     * @param amount_ - The amount of tokens to be withdrawn
     * @param requestId_ - ID of the withdrawal request
     **/
    function withdraw(
        uint256 userL1Address_,
        uint256 ticker_,
        uint256 amount_,
        uint256 requestId_
    ) external {
        require(uint256(uint160(msg.sender)) == userL1Address_, "Sender is not withdrawal recipient");
        uint256 userL2Address = l2ContractAddress[userL1Address_];

        // Construct withdrawal message payload.
        uint256[] memory withdrawal_payload = new uint256[](5);
        withdrawal_payload[0] = WITHDRAWAL_INDEX;
        withdrawal_payload[1] = userL1Address_;
        withdrawal_payload[2] = ticker_;
        withdrawal_payload[3] = amount_;
        withdrawal_payload[4] = requestId_;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(userL2Address, withdrawal_payload);

        address tokenContract = tokenContractAddress[ticker_];
        IERC20(tokenContract).safeTransfer(msg.sender, amount_);

        // Construct update withdrawal request message payload.
        uint256[] memory updateWithdrawalRequestPayload = new uint256[](2);
        updateWithdrawalRequestPayload[0] = userL2Address;
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
     * @param userL1Address_ - Users L1 wallet address
     * @param amount_ - The amount of tokens to be withdrawn
     * @param requestId_ - ID of the withdrawal request
     **/
    function withdrawEth(
        uint256 userL1Address_,
        uint256 amount_,
        uint256 requestId_
    ) external {
        require(uint256(uint160(msg.sender)) == userL1Address_, "Sender is not withdrawal recipient");
        uint256 userL2Address = l2ContractAddress[userL1Address_];

        // Construct withdrawal message payload.
        uint256[] memory withdrawal_payload = new uint256[](5);
        withdrawal_payload[0] = WITHDRAWAL_INDEX;
        withdrawal_payload[1] = userL1Address_;
        withdrawal_payload[2] = ETH_TICKER;
        withdrawal_payload[3] = amount_;
        withdrawal_payload[4] = requestId_;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(userL2Address, withdrawal_payload);

        payable(msg.sender).transfer(amount_);

        // Construct update withdrawal request message payload.
        uint256[] memory updateWithdrawalRequestPayload = new uint256[](2);
        updateWithdrawalRequestPayload[0] = userL2Address;
        updateWithdrawalRequestPayload[1] = requestId_;

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
        onlyOwner
    {
        require(recipient_ != address(0), "Token Transfer failed: recipient address is zero");
        require(amount_ >= 0, "Token Transfer failed: amount is zero");
        IERC20(tokenAddress_).safeTransfer(recipient_, amount_);
    }

    /**
     * @dev function to transfer funds from this contract to another address
     * @param recipient_ - address of the recipient
     * @param amount_ - amount that needs to be transferred
     **/
    function transferEth(address payable recipient_, uint256 amount_)
        external
        onlyOwner
    {
        require(recipient_ != address(0), "ETH Transfer failed: recipient address is zero");
        require(amount_ >= 0, "ETH Transfer failed: amount is zero");
        recipient_.transfer(amount_);
    }
}