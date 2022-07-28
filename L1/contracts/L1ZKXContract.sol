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

    event LogContractInitialized(
        IStarknetCore starknetCore,
        uint256 assetContractAddress,
        uint256 withdrawalRequestContractAddress
    );

    event LogDeposit(
        address indexed sender,
        uint256 amount,
        uint256 indexed collateralId,
        uint256 indexed l2Recipient,
        bytes32 msgHash
    );

    event LogWithdrawal(
        address indexed recipient,
        uint256 indexed ticker,
        uint256 amount,
        uint256 requestId,
        bytes32 msgHash
    );

    event LogAssetListUpdated(uint256 ticker, uint256 collateralId);

    event LogAssetRemovedFromList(uint256 ticker, uint256 collateralId);

    event LogTokenContractAddressUpdated(
        uint256 indexed ticker,
        address indexed tokenContractAddresses
    );

    struct Asset {
        bool exists;
        uint32 index;
        address contractAddress;
        uint256 collateralID;
    }

    event LogAssetContractAddressChanged(
        uint256 oldAssetContract,
        uint256 newAssetContract
    );

    event LogWithdrawalRequestContractChanged(
        uint256 oldWithdrawalContract,
        uint256 newWithdrawalContract
    );

    event LogAdminTransferFunds(
        address indexed recipient,
        uint256 amount,
        address indexed tokenAddress
    );

    event LogAdminTransferEth(address payable indexed recipient, uint256 amount);

    // The StarkNet core contract.
    IStarknetCore public starknetCore;

    // List of assets
    uint256[] public assetList;

    mapping(uint256 => AssetInfo) private assetsByTicker;

    // Maps L1 metamask account address to the l2 account contract address
    mapping(uint256 => uint256) public l2ContractAddress;

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

        emit LogContractInitialized(
            starknetCore_,
            assetContractAddress_,
            withdrawalRequestContractAddress_
        );
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
        require(
            assetInfoByTicker[ticker_].exists == false, 
            "Failed to add asset: Ticker already present"
        );
        // Construct the update asset list message's payload.
        uint256[] memory payload = new uint256[](3);
        payload[0] = ADD_ASSET_INDEX;
        payload[1] = ticker_;
        payload[2] = assetId_;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(assetContractAddress, payload);
        
        assetsByTicker[ticker_] = Asset({
            exists: true,
            index: uint32(assetList.length()),
            contractAddress: address(0),
            collateralID: assetId_
        });
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
        Asset storage assetToRemove = assetsByTicker[ticker_];
        require(assetToRemove.exists, "Failed to remove non-existing asset");
        
        uint32 toRemoveIndex = assetToRemove.index;
        uint256 lastAssetIndex = assetList.length - 1;
        uint256 lastAssetTicker = assetList[lastAssetIndex];
        Asset storage lastAsset = assetsByTicker[lastAssetTicker];
        lastAsset.index = toRemoveIndex;
        assetList[uint256(toRemoveIndex)] = lastAsset.ticker;
        assetList.pop();
        delete assetToRemove;

        // Construct the remove asset message's payload.
        uint256[] memory payload = new uint256[](3);
        payload[0] = REMOVE_ASSET_INDEX;
        payload[1] = ticker_;
        payload[2] = assetId_;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(assetContractAddress, payload);

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
        require(
            tokenContractAddress_ != address(0), 
            "Failed to set token address: New address is 0"
        );
        Asset storage asset = assetByTicker[ticker_];
        require(
            asset.contractAddress == address(0), 
            "Failed to set token address: Already set"
        );
        asset.contractAddress = tokenContractAddress_;
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
        uint256 oldAssetContractAddress = assetContractAddress;
        assetContractAddress = assetContractAddress_;
        emit LogAssetContractAddressChanged(
            oldAssetContractAddress,
            assetContractAddress_
        );
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
        uint256 oldWithdrawalRequestContractAddress = withdrawalRequestContractAddress;
        withdrawalRequestContractAddress = withdrawalRequestAddress_;
        emit LogWithdrawalRequestContractChanged(
            oldWithdrawalRequestContractAddress,
            withdrawalRequestAddress_
        );
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
    ) private {

        // Construct the deposit message's payload.
        uint256[] memory depositPayload = new uint256[](3);
        depositPayload[0] = userL1Address_;
        depositPayload[1] = amount_;
        depositPayload[2] = collateralId_;

        // Send the message to the StarkNet core contract.
        bytes32 msgHash = starknetCore.sendMessageToL2(
            userL2Address_,
            DEPOSIT_SELECTOR,
            depositPayload
        );

        emit LogDeposit(
            msg.sender,
            amount_,
            collateralId_,
            userL2Address_,
            msgHash
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
        // Prepare transfer
        Asset memory asset = assetsByTicker[ticker_];
        require(asset.exists, "Failed to deposit non-registered asset");
        require(asset.contractAddress != address(0), "Deposit failed: Contract address not set");
        uint256 senderAsUint256 = uint256(uint160(address(msg.sender)));
        IERC20 Token = IERC20(asset.contractAddress);
        address zkxAddress = address(this);

        // Transfer funds
        uint256 zkxBalanceBefore = Token.balanceOf(zkxAddress);
        Token.safeTransferFrom(msg.sender, zkxAddress, amount_);
        uint256 zkxBalanceAfter = Token.balanceOf(zkxAddress);
        require(zkxBalanceAfter >= zkxBalanceBefore + amount_, "Deposit failed: Invalid transfer amount");

        // Submit deposit
        depositToL2(
            senderAsUint256,
            userL2Address_,
            asset.id,
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
        uint256 senderAsUint256 = uint256(uint160(address(msg.sender)));
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
     * @param userL1Address_ - User's L1 Account address
     * @param userL2Address_ - User's L2 Account address
     * @param ticker_ - felt representation of the ticker
     * @param amount_ - The amount of tokens to be withdrawn
     * @param requestId_ - ID of the withdrawal request
     **/
    function withdraw(
        address userL1Address_,
        uint256 userL2Address_,
        uint256 ticker_,
        uint256 amount_,
        uint256 requestId_
    ) external {

        Asset memory asset = assetsByTicker[ticker_];
        require(asset.exists, "Withdrawal failed: non-registered asset");
        require(asset.contractAddress != address(0), "Withdrawal failed: Contract address not set");

        // Construct withdrawal message payload.
        uint256[] memory withdrawal_payload = new uint256[](5);
        withdrawal_payload[0] = WITHDRAWAL_INDEX;
        withdrawal_payload[1] = uint256(uint160(userL1Address_));
        withdrawal_payload[2] = ticker_;
        withdrawal_payload[3] = amount_;
        withdrawal_payload[4] = requestId_;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(userL2Address_, withdrawal_payload);

        // Construct update withdrawal request message payload.
        uint256[] memory updateWithdrawalRequestPayload = new uint256[](2);
        updateWithdrawalRequestPayload[0] = userL2Address_;
        updateWithdrawalRequestPayload[1] = requestId_;

        // Send the message to the StarkNet core contract.
        bytes32 msgHash = starknetCore.sendMessageToL2(
            withdrawalRequestContractAddress,
            UPDATE_WITHDRAWAL_REQUEST_SELECTOR,
            updateWithdrawalRequestPayload
        );

        address tokenContract = tokenContractAddress[ticker_];
        IERC20(tokenContract).safeTransfer(userL1Address_, amount_);

        emit LogWithdrawal(userL1Address_, ticker_, amount_, requestId_, msgHash);
    }

    /**
     * @dev function to withdraw funds from an L2 Account contract
     * @param userL1Address_ - User's L1 Account address
     * @param userL2Address_ - User's L2 Account address
     * @param amount_ - The amount of tokens to be withdrawn
     * @param requestId_ - ID of the withdrawal request
     **/
    function withdrawEth(
        address userL1Address_,
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

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(userL2Address_, withdrawal_payload);

        // Construct update withdrawal request message payload.
        uint256[] memory updateWithdrawalRequestPayload = new uint256[](2);
        updateWithdrawalRequestPayload[0] = userL2Address_;
        updateWithdrawalRequestPayload[1] = requestId_;

        // Send the message to the StarkNet core contract.
        bytes32 msgHash = starknetCore.sendMessageToL2(
            withdrawalRequestContractAddress,
            UPDATE_WITHDRAWAL_REQUEST_SELECTOR,
            updateWithdrawalRequestPayload
        );

        payable(userL1Address_).transfer(amount_);

        emit LogWithdrawal(userL1Address_, ETH_TICKER, amount_, requestId_, msgHash);
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

        emit LogAdminTransferFunds(recipient_, amount_, tokenAddress_);
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

        emit LogAdminTransferEth(recipient_, amount_);
    }
}