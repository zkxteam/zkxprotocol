// SPDX-License-Identifier: Apache-2.0.
pragma solidity 0.8.14;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "./IStarknetCore.sol";
import "./Constants.sol";

// Contract for L1 <-> L2 interaction between an L2 contracts and this L1 ZKX contract.
contract L1ZKXContract is Ownable, ReentrancyGuard {

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
        address indexed tokenContractAddress
    );

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

    struct Asset {
        bool exists;
        address tokenAddress;
        uint256 index;
        uint256 collateralID;
    }

    /// The StarkNet core contract
    IStarknetCore public starknetCore;

    /// List of assets tickers
    uint256[] public assetList;

    /// L2 ZKX AssetContract address
    uint256 public assetContractAddress;

    /// L2 ZKX WithdrawalRequestContract address
    uint256 public withdrawalRequestContractAddress;

    /// Assets by ticker
    mapping(uint256 => Asset) private assetsByTicker;

    /// Modifier to verify valid L2 address.
    modifier isValidL2Address(uint256 l2Address_) {
        require(l2Address_ != 0 && l2Address_ < FIELD_PRIME, "L2_ADDRESS_OUT_OF_RANGE");
        _;
    }

    /// @param starknetCore_ StarknetCore contract address used for L1-to-L2 messaging
    /// @param assetContractAddress_ L2 ZKX AssetContract address
    /// @param withdrawalRequestContractAddress_ L2 ZKX WithdrawalReuqestContract address
    constructor(
        IStarknetCore starknetCore_,
        uint256 assetContractAddress_,
        uint256 withdrawalRequestContractAddress_
    ) 
        isValidL2Address(assetContractAddress_) 
        isValidL2Address(withdrawalRequestContractAddress_) 
    {
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

    /// @dev function to update asset list in L1
    /// @param ticker_ - felt representation of the ticker
    /// @param assetId_ - Id of the asset created
    function updateAssetListInL1(uint256 ticker_, uint256 assetId_)
        external
        onlyOwner
    {   
        // Add asset
        require(
            assetsByTicker[ticker_].exists == false, 
            "Failed to add asset: Ticker already exists"
        );
        assetsByTicker[ticker_] = Asset({
            exists: true,
            tokenAddress: address(0),
            index: assetList.length,
            collateralID: assetId_
        });
        assetList.push(ticker_);

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        uint256[] memory payload = new uint256[](3);
        payload[0] = ADD_ASSET_INDEX;
        payload[1] = ticker_;
        payload[2] = assetId_;
        starknetCore.consumeMessageFromL2(assetContractAddress, payload);

        emit LogAssetListUpdated(ticker_, assetId_);
    }

    /// @dev function to remove asset from list in L1
    /// @param ticker_ - felt representation of the ticker
    /// @param assetId_ - Id of the asset to be removed
    function removeAssetFromList(uint256 ticker_, uint256 assetId_)
        external
        onlyOwner
    {
        require(assetList.length > 0, "Nothing to remove");

        // Prepare asset to remove
        Asset storage assetToRemove = assetsByTicker[ticker_];
        uint256 toRemoveIndex = assetToRemove.index;
        require(assetToRemove.exists, "Failed to remove non-existing asset");
        
        // Prepare asset for swap
        uint256 lastAssetIndex = assetList.length - 1;
        uint256 lastAssetTicker = assetList[lastAssetIndex];
        Asset storage lastAsset = assetsByTicker[lastAssetTicker];

        // Swap and delete last
        lastAsset.index = toRemoveIndex;
        assetList[toRemoveIndex] = lastAssetTicker;
        assetList.pop();
        delete assetsByTicker[ticker_];

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        uint256[] memory payload = new uint256[](3);
        payload[0] = REMOVE_ASSET_INDEX;
        payload[1] = ticker_;
        payload[2] = assetId_;
        starknetCore.consumeMessageFromL2(assetContractAddress, payload);

        emit LogAssetRemovedFromList(ticker_, assetId_);
    }

    /// @dev Function to get the list of available assets
    /// @return List of available asset tickers
    function getAssetList() external view returns (uint256[] memory) {
        return assetList;
    }

    /// @dev Function to get asset contract address by its ticker
    /// @return Token contract address
    function tokenContractAddress(uint256 ticker_) external view returns (address) {
        return assetsByTicker[ticker_].tokenAddress;
    }

    /// @dev Function to get asset ID by its ticker
    /// @return Asset collateral ID
    function assetID(uint256 ticker_) external view returns (uint256) {
        return assetsByTicker[ticker_].collateralID;
    }

    /// @dev function to set token contract address
    /// @param ticker_ - felt representation of the ticker
    /// @param tokenContractAddress_ - address of the token contract
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
            "Failed to set token address: zero address provided"
        );
        Asset storage asset = assetsByTicker[ticker_];
        require(
            asset.exists,
            "Failed to set token address: non-registered asset"
        );
        require(
            asset.tokenAddress == address(0), 
            "Failed to set token address: Already set"
        );
        asset.tokenAddress = tokenContractAddress_;
        emit LogTokenContractAddressUpdated(ticker_, tokenContractAddress_);
    }

    /// @dev function to set asset contract address
    /// @param assetContractAddress_ - address of the asset contract
    function setAssetContractAddress(uint256 assetContractAddress_)
        external
        onlyOwner
        isValidL2Address(assetContractAddress_)
    {
        emit LogAssetContractAddressChanged(
            assetContractAddress,
            assetContractAddress_
        );
        assetContractAddress = assetContractAddress_;   
    }

    /// @dev function to set withdrawal request contract address
    /// @param withdrawalRequestAddress_ - address of withdrawal request contract
    function setWithdrawalRequestAddress(uint256 withdrawalRequestAddress_)
        external
        onlyOwner
        isValidL2Address(withdrawalRequestAddress_)
    {   
        emit LogWithdrawalRequestContractChanged(
            withdrawalRequestContractAddress,
            withdrawalRequestAddress_
        );
        withdrawalRequestContractAddress = withdrawalRequestAddress_;
    }

    /// @dev function to deposit funds to L2 Account contract
    /// @param userL1Address_ - L1 user address
    /// @param userL2Address_ - L2 address of user's ZKX account
    /// @param collateralId_ - ID of the collateral
    /// @param amount_ - The amount of tokens to be deposited
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

    /// @dev function to deposit funds to L1ZKX contract
    /// @param userL2Address_ - The L2 account address of the user
    /// @param ticker_ - felt representation of the ticker
    /// @param amount_ - The amount of collateral to be deposited
    function depositToL1(
        uint256 userL2Address_,
        uint256 ticker_,
        uint256 amount_
    ) 
        external 
        nonReentrant 
        isValidL2Address(userL2Address_)
    {   
        // Prepare transfer
        Asset memory asset = assetsByTicker[ticker_];
        require(asset.exists, "Deposit failed: non-registered asset");
        require(asset.tokenAddress != address(0), "Deposit failed: token address not set");
        uint256 senderAsUint256 = uint256(uint160(address(msg.sender)));
        IERC20 Token = IERC20(asset.tokenAddress);
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
            asset.collateralID,
            amount_
        );
    }

    /// @dev function to deposit ETH to L1ZKX contract
    /// @param userL2Address_ - The L2 account address of the user
    function depositEthToL1(uint256 userL2Address_) 
        payable 
        external 
        nonReentrant
        isValidL2Address(userL2Address_)
    {
        require(msg.value > 0, "Deposit failed: no value provided");
        Asset storage ethAsset = assetsByTicker[ETH_TICKER];
        require(ethAsset.exists, "Deposit failed: ETH not registered as asset");
        uint256 senderAsUint256 = uint256(uint160(address(msg.sender)));
        depositToL2(
            senderAsUint256,
            userL2Address_,
            ethAsset.collateralID,
            msg.value
        );
    }

    /// @dev function to withdraw funds from an L2 Account contract
    /// @param userL1Address_ - User's L1 Account address
    /// @param userL2Address_ - User's L2 Account address
    /// @param ticker_ - felt representation of the ticker
    /// @param amount_ - The amount of tokens to be withdrawn
    /// @param requestId_ - ID of the withdrawal request
    function withdraw(
        address userL1Address_,
        uint256 userL2Address_,
        uint256 ticker_,
        uint256 amount_,
        uint256 requestId_
    ) external nonReentrant {

        Asset memory asset = assetsByTicker[ticker_];
        require(asset.exists, "Withdrawal failed: non-registered asset");
        require(asset.tokenAddress != address(0), "Withdrawal failed: token address not set");

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

        IERC20(asset.tokenAddress).safeTransfer(userL1Address_, amount_);

        emit LogWithdrawal(userL1Address_, ticker_, amount_, requestId_, msgHash);
    }

    /// @dev function to withdraw funds from an L2 Account contract
    /// @param userL1Address_ - User's L1 Account address
    /// @param userL2Address_ - User's L2 Account address
    /// @param amount_ - The amount of tokens to be withdrawn
    /// @param requestId_ - ID of the withdrawal request
    function withdrawEth(
        address userL1Address_,
        uint256 userL2Address_,
        uint256 amount_,
        uint256 requestId_
    ) external nonReentrant {
        
        require(
            assetsByTicker[ETH_TICKER].exists, 
            "Deposit failed: ETH not registered as asset"
        );

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

    /// @dev function to transfer funds from this contract to another address
    /// @param recipient_ - address of the recipient
    /// @param amount_ - amount that needs to be transferred
    /// @param tokenAddress_ - address of the token contract
    function transferFunds(address recipient_, uint256 amount_, address tokenAddress_)
        external
        onlyOwner
    {
        require(recipient_ != address(0), "Token Transfer failed: recipient address is zero");
        require(amount_ >= 0, "Token Transfer failed: amount is zero");
        IERC20(tokenAddress_).safeTransfer(recipient_, amount_);

        emit LogAdminTransferFunds(recipient_, amount_, tokenAddress_);
    }

    /// @dev function to transfer funds from this contract to another address
    /// @param recipient_ - address of the recipient
    /// @param amount_ - amount that needs to be transferred
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