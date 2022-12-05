// SPDX-License-Identifier: Apache-2.0.
pragma solidity 0.8.14;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "./IStarknetCore.sol";
import "./Constants.sol";

// Contract for L1 <-> L2 interaction between an L2 contracts and this L1 ZKX contract
contract L1ZKXContract is Ownable, ReentrancyGuard {

    using SafeERC20 for IERC20;

    //////////////
    /// Events ///
    //////////////

    event LogContractInitialized(
        IStarknetCore starknetCore,
        uint256 assetContractAddress,
        uint256 withdrawalRequestContractAddress
    );

    event LogDeposit(
        address indexed sender,
        uint256 amount,
        uint256 indexed assetId,
        uint256 indexed l2Recipient,
        bytes32 msgHash
    );

    event LogWithdrawal(
        address indexed recipient,
        uint256 indexed assetId,
        uint256 amount,
        uint256 requestId,
        bytes32 msgHash
    );

    event LogAssetListUpdated(uint256 assetId);

    event LogAssetRemovedFromList(uint256 assetId);

    event LogTokenContractAddressUpdated(
        uint256 indexed assetId,
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

    event LogAdminTransferEth(
        address payable indexed recipient,
        uint256 amount
    );

    event LogDepositCancelRequest(
        address indexed sender,
        uint256 indexed l2Recipient,
        uint256 indexed assetId,
        uint256 amount,
        uint256 nonce
    );

    event LogDepositReclaimed(
        address indexed sender,
        uint256 indexed l2Recipient,
        uint256 indexed assetId,
        uint256 amount,
        uint256 nonce
    );

    //////////////////////
    /// Internal types ///
    //////////////////////

    struct Asset {
        bool exists;
        uint16 index;
        address tokenAddress;
    }

    ///////////////
    /// Storage ///
    ///////////////

    /// The StarkNet core contract
    IStarknetCore immutable public starknetCore;

    /// List of assets IDs
    uint256[] public assetList;

    /// L2 ZKX AssetContract address
    uint256 public assetContractAddress;

    /// L2 ZKX WithdrawalRequestContract address
    uint256 public withdrawalRequestContractAddress;

    /// Assets stored by their IDs
    mapping(uint256 => Asset) private assetsById;

    ///////////////////
    /// Constructor ///
    ///////////////////

    /// @param starknetCore_ StarknetCore contract address used for L1-to-L2 messaging
    /// @param assetContractAddress_ L2 ZKX AssetContract address
    /// @param withdrawalRequestContractAddress_ L2 ZKX WithdrawalReuqestContract address
    constructor(
        IStarknetCore starknetCore_,
        uint256 assetContractAddress_,
        uint256 withdrawalRequestContractAddress_
    ) {
        require(address(starknetCore_) != address(0));
        require(isValidFelt(assetContractAddress_));
        require(isValidFelt(withdrawalRequestContractAddress_));

        starknetCore = starknetCore_;
        assetContractAddress = assetContractAddress_;
        withdrawalRequestContractAddress = withdrawalRequestContractAddress_;

        emit LogContractInitialized(
            starknetCore_,
            assetContractAddress_,
            withdrawalRequestContractAddress_
        );
    }

    //////////////////////
    /// View functions ///
    //////////////////////

    /// @dev Function to get the list of available assets
    /// @return List of available asset IDs
    function getAssetList() external view returns (uint256[] memory) {
        return assetList;
    }

    /// @dev Function to check if asset already exists
    /// @return Bool value, true is exists, false otherwise
    function assetExists(uint256 assetId_) external view returns (bool) {
        return assetsById[assetId_].exists;
    }

    /// @dev Function to get asset contract address by its ID
    /// @return Token contract address
    function tokenContractAddress(uint256 assetId_) external view returns (address) {
        return assetsById[assetId_].tokenAddress;
    }

    ///////////////////
    /// Withdrawals ///
    ///////////////////

    /// @dev function to withdraw funds from an L2 Account contract
    /// @param userL1Address_ - User's L1 Account address
    /// @param assetId_ - Asset ID
    /// @param amount_ - The amount of tokens to be withdrawn
    /// @param requestId_ - ID of the withdrawal request
    function withdraw(
        address userL1Address_,
        uint256 assetId_,
        uint256 amount_,
        uint256 requestId_
    ) external nonReentrant {
        Asset memory asset = assetsById[assetId_];
        require(asset.exists, "Withdrawal failed: non-registered asset");
        require(
            asset.tokenAddress != address(0),
            "Withdrawal failed: token address not set"
        );

        // Consume call will revert if no matching message exists
        starknetCore.consumeMessageFromL2(
            withdrawalRequestContractAddress,
            withdrawalMessagePayload(
                uint256(uint160(userL1Address_)),
                assetId_,
                amount_,
                requestId_
            )
        );

        // Construct update withdrawal request message payload
        uint256[] memory updateWithdrawalRequestPayload = new uint256[](1);
        updateWithdrawalRequestPayload[0] = requestId_;

        // Send the message to the StarkNet core contract
        bytes32 msgHash = starknetCore.sendMessageToL2(
            withdrawalRequestContractAddress,
            UPDATE_WITHDRAWAL_REQUEST_SELECTOR,
            updateWithdrawalRequestPayload
        );

        IERC20(asset.tokenAddress).safeTransfer(userL1Address_, amount_);

        emit LogWithdrawal(
            userL1Address_,
            assetId_,
            amount_,
            requestId_,
            msgHash
        );
    }

    /// @dev function to withdraw funds from an L2 Account contract
    /// @param userL1Address_ - User's L1 Account address
    /// @param amount_ - The amount of tokens to be withdrawn
    /// @param requestId_ - ID of the withdrawal request
    function withdrawEth(
        address userL1Address_,
        uint256 amount_,
        uint256 requestId_
    ) external nonReentrant {
        require(
            assetsById[ETH_ID].exists,
            "Withdraw failed: ETH not registered as asset"
        );

        // Consume call will revert if no matching message exists
        starknetCore.consumeMessageFromL2(
            withdrawalRequestContractAddress,
            withdrawalMessagePayload(
                uint256(uint160(userL1Address_)),
                ETH_ID,
                amount_,
                requestId_
            )
        );

        // Construct update withdrawal request message payload
        uint256[] memory updateWithdrawalRequestPayload = new uint256[](1);
        updateWithdrawalRequestPayload[0] = requestId_;

        // Send the message to the StarkNet core contract
        bytes32 msgHash = starknetCore.sendMessageToL2(
            withdrawalRequestContractAddress,
            UPDATE_WITHDRAWAL_REQUEST_SELECTOR,
            updateWithdrawalRequestPayload
        );
        
        (bool isSuccess,) = userL1Address_.call{value: amount_}("");
        require(isSuccess, "Withdrawal failed: ETH Transfer failed");

        emit LogWithdrawal(
            userL1Address_,
            ETH_ID,
            amount_,
            requestId_,
            msgHash
        );
    }

    ////////////////////
    ///// Deposits /////
    ////////////////////

    /// @dev function to deposit funds to L1ZKX contract
    /// @param userL2Address_ - The L2 account address of the user
    /// @param assetId_ - Asset ID
    /// @param amount_ - The amount of collateral to be deposited
    function depositToL1(
        uint256 userL2Address_,
        uint256 assetId_,
        uint256 amount_
    ) external nonReentrant {   
        // Validate input
        require(isValidFelt(userL2Address_), "INVALID_FELT: userL2Address_");
        require(isValidFelt(amount_), "INVALID_FELT: amount_");

        // Prepare transfer
        Asset memory asset = assetsById[assetId_];
        require(asset.exists, "Deposit failed: non-registered asset");
        require(
            asset.tokenAddress != address(0),
            "Deposit failed: token address not set"
        );
        uint256 senderAsUint256 = uint256(uint160(msg.sender));
        IERC20 Token = IERC20(asset.tokenAddress);
        address zkxAddress = address(this);

        // Transfer funds
        uint256 zkxBalanceBefore = Token.balanceOf(zkxAddress);
        Token.safeTransferFrom(msg.sender, zkxAddress, amount_);
        uint256 zkxBalanceAfter = Token.balanceOf(zkxAddress);
        require(
            zkxBalanceAfter >= zkxBalanceBefore + amount_,
            "Deposit failed: Invalid transfer amount"
        );

        // Submit deposit
        depositToL2(
            senderAsUint256,
            userL2Address_,
            assetId_,
            amount_
        );
    }

    /// @dev function to deposit ETH to L1ZKX contract
    /// @param userL2Address_ - The L2 account address of the user
    function depositEthToL1(uint256 userL2Address_)
        external
        payable
        nonReentrant
    {
        require(isValidFelt(userL2Address_), "INVALID_FELT: userL2Address_");
        require(msg.value > 0, "Deposit failed: no value provided");

        Asset storage ethAsset = assetsById[ETH_ID];
        require(ethAsset.exists, "Deposit failed: ETH not registered as asset");
        uint256 senderAsUint256 = uint256(uint160(msg.sender));
        depositToL2(
            senderAsUint256,
            userL2Address_,
            ETH_ID,
            msg.value
        );
    }

    /// @dev function to cancel deposit funds to L2 Account contract
    /// @param userL2Address_ - L2 address of user's ZKX account
    /// @param assetId_ - felt representation of asset ID
    /// @param amount_ - The amount of tokens to be deposited
    /// @param nonce_ - L1 to L2 deposit message nonce
    function depositCancelRequest(
        uint256 userL2Address_,
        uint256 assetId_,
        uint256 amount_,
        uint256 nonce_
    ) external nonReentrant {
        Asset memory asset = assetsById[assetId_];
        require(
            asset.exists,
            "Failed to initiate deposit cancel request: non-existing asset"
        );

        starknetCore.startL1ToL2MessageCancellation(
            userL2Address_,
            DEPOSIT_SELECTOR,
            depositMessagePayload(
                uint256(uint160(msg.sender)),
                amount_,
                assetId_
            ),
            nonce_
        );

        emit LogDepositCancelRequest(
            msg.sender,
            userL2Address_,
            assetId_,
            amount_,
            nonce_
        );
    }

    /// @dev function to finalize cancel deposit funds to L2 Account contract
    /// @param userL2Address_ - L2 address of user's ZKX account
    /// @param assetId_ - Asset ID
    /// @param amount_ - The amount of tokens to be deposited
    /// @param nonce_ - L1 to L2 deposit message nonce
    function depositReclaim(
        uint256 userL2Address_,
        uint256 assetId_,
        uint256 amount_,
        uint256 nonce_
    ) external nonReentrant {
        Asset memory asset = assetsById[assetId_];
        require(
            asset.exists,
            "Failed to call deposit reclaim: non-existing asset"
        );

        starknetCore.cancelL1ToL2Message(
            userL2Address_,
            DEPOSIT_SELECTOR,
            depositMessagePayload(
                uint256(uint160(msg.sender)),
                amount_,
                assetId_
            ),
            nonce_
        );

        if (assetId_ == ETH_ID) {
            (bool isSuccess,) = msg.sender.call{value: amount_}("");
            require(isSuccess, "Deposit reclaim failed: ETH Transfer failed");
        } else {
            IERC20(asset.tokenAddress).safeTransfer(msg.sender, amount_);
        }

        emit LogDepositReclaimed(
            msg.sender,
            userL2Address_,
            assetId_,
            amount_,
            nonce_
        );
    }

    ///////////////////////
    /// Owner functions ///
    ///////////////////////

    /// @dev function to set token contract address
    /// @param assetId_ - Asset ID
    /// @param tokenContractAddress_ - address of the token contract
    function setTokenContractAddress(
        uint256 assetId_,
        address tokenContractAddress_
    ) external onlyOwner {
        require(
            tokenContractAddress_ != address(0),
            "Failed to set token address: zero address provided"
        );
        Asset storage asset = assetsById[assetId_];
        require(
            asset.exists,
            "Failed to set token address: non-registered asset"
        );
        require(
            asset.tokenAddress == address(0),
            "Failed to set token address: Already set"
        );
        asset.tokenAddress = tokenContractAddress_;
        emit LogTokenContractAddressUpdated(assetId_, tokenContractAddress_);
    }

    /// @dev function to set asset contract address
    /// @param assetContractAddress_ - address of the asset contract
    function setAssetContractAddress(uint256 assetContractAddress_) external onlyOwner {
        require(isValidFelt(assetContractAddress_), "INVALID_FELT: assetContractAddress_");

        emit LogAssetContractAddressChanged(
            assetContractAddress,
            assetContractAddress_
        );
        assetContractAddress = assetContractAddress_;
    }

    /// @dev function to set withdrawal request contract address
    /// @param withdrawalRequestAddress_ - address of withdrawal request contract
    function setWithdrawalRequestAddress(uint256 withdrawalRequestAddress_) external onlyOwner {
        require(isValidFelt(withdrawalRequestAddress_), "INVALID_FELT: withdrawalRequestAddress_");

        emit LogWithdrawalRequestContractChanged(
            withdrawalRequestContractAddress,
            withdrawalRequestAddress_
        );
        withdrawalRequestContractAddress = withdrawalRequestAddress_;
    }

    /// @dev function to update asset list in L1
    /// @param assetId_ - Id of the asset created
    function updateAssetListInL1(uint256 assetId_)
        external
        onlyOwner
        nonReentrant
    {
        // Add asset
        require(
            assetsById[assetId_].exists == false,
            "Failed to add asset: Asset ID already exists"
        );
        assetsById[assetId_] = Asset({
            exists: true,
            index: uint16(assetList.length),
            tokenAddress: address(0)
        });
        assetList.push(assetId_);

        // Consume call will revert if no matching message exists
        uint256[] memory payload = new uint256[](2);
        payload[0] = ADD_ASSET_INDEX;
        payload[1] = assetId_;
        starknetCore.consumeMessageFromL2(assetContractAddress, payload);

        emit LogAssetListUpdated(assetId_);
    }

    /// @dev function to remove asset from list in L1
    /// @param assetId_ - Id of the asset to be removed
    function removeAssetFromList(uint256 assetId_)
        external
        onlyOwner
        nonReentrant
    {
        require(assetList.length > 0, "Nothing to remove");

        // Prepare asset to remove
        Asset storage assetToRemove = assetsById[assetId_];
        uint16 toRemoveIndex = assetToRemove.index;
        require(assetToRemove.exists, "Failed to remove non-existing asset");

        // Prepare asset for swap
        uint256 lastAssetIndex = assetList.length - 1;
        uint256 lastAssetId = assetList[lastAssetIndex];
        Asset storage lastAsset = assetsById[lastAssetId];

        // Swap and delete last
        lastAsset.index = toRemoveIndex;
        assetList[uint256(toRemoveIndex)] = lastAssetId;
        assetList.pop();
        delete assetsById[assetId_];

        // Consume call will revert if no matching message exists
        uint256[] memory payload = new uint256[](2);
        payload[0] = REMOVE_ASSET_INDEX;
        payload[1] = assetId_;
        starknetCore.consumeMessageFromL2(assetContractAddress, payload);

        emit LogAssetRemovedFromList(assetId_);
    }

    /// @dev function to transfer funds from this contract to another address
    /// @param recipient_ - address of the recipient
    /// @param amount_ - amount that needs to be transferred
    /// @param tokenAddress_ - address of the token contract
    function transferFunds(
        address recipient_,
        uint256 amount_,
        address tokenAddress_
    ) external onlyOwner {
        require(
            recipient_ != address(0),
            "Token Transfer failed: recipient address is zero"
        );
        require(amount_ >= 0, "Token Transfer failed: amount is zero");
        IERC20(tokenAddress_).safeTransfer(recipient_, amount_);

        emit LogAdminTransferFunds(recipient_, amount_, tokenAddress_);
    }

    /// @dev function to transfer funds from this contract to another address
    /// @param recipient_ - address of the recipient
    /// @param amount_ - amount that needs to be transferred
    function transferEth(
        address payable recipient_, 
        uint256 amount_
    )
        external
        onlyOwner
    {
        require(
            recipient_ != address(0),
            "ETH Transfer failed: recipient address is zero"
        );
        require(amount_ >= 0, "ETH Transfer failed: amount is zero");
        (bool isSuccess,) = recipient_.call{value: amount_}("");
        require(isSuccess, "ETH Transfer failed");

        emit LogAdminTransferEth(recipient_, amount_);
    }

    /////////////////////////
    /// Private functions ///
    /////////////////////////

    /// @dev function to deposit funds to L2 Account contract
    /// @param userL1Address_ - L1 user address
    /// @param userL2Address_ - L2 address of user's ZKX account
    /// @param assetId_ - Asset ID
    /// @param amount_ - The amount of tokens to be deposited
    function depositToL2(
        uint256 userL1Address_,
        uint256 userL2Address_,
        uint256 assetId_,
        uint256 amount_
    ) private {
        // Send the message to the StarkNet core contract
        bytes32 msgHash = starknetCore.sendMessageToL2(
            userL2Address_,
            DEPOSIT_SELECTOR,
            depositMessagePayload(userL1Address_, amount_, assetId_)
        );

        emit LogDeposit(
            msg.sender,
            amount_,
            assetId_,
            userL2Address_,
            msgHash
        );
    }

    /// @dev function to get deposit message payload
    /// @param userL1Address_ - L1 user address
    /// @param amount_ - The amount of tokens to be deposited
    /// @param assetId_ - Asset ID
    function depositMessagePayload(
        uint256 userL1Address_,
        uint256 amount_,
        uint256 assetId_
    ) private pure returns (uint256[] memory) {
        uint256[] memory payload = new uint256[](3);
        payload[0] = userL1Address_;
        payload[1] = amount_;
        payload[2] = assetId_;
        return payload;
    }

    /// @dev function to get withdrawal message payload
    /// @param userL1Address_ - L1 user address
    /// @param assetId_ - Asset ID
    /// @param amount_ - The amount of tokens to be deposited
    /// @param requestId_ - ID of the withdrawal request
    function withdrawalMessagePayload(
        uint256 userL1Address_,
        uint256 assetId_,
        uint256 amount_,
        uint256 requestId_
    ) private pure returns (uint256[] memory) {
        uint256[] memory payload = new uint256[](5);
        payload[0] = WITHDRAWAL_INDEX;
        payload[1] = userL1Address_;
        payload[2] = assetId_;
        payload[3] = amount_;
        payload[4] = requestId_;
        return payload;
    }

    /// @dev Checks if value is a valid Cairo felt
    /// @param value_ - Value to be checked
    /// @return isValid - Validation result
    function isValidFelt(uint256 value_) private pure returns (bool isValid) {
        return value_ != 0 && value_ < FIELD_PRIME;
    }
}
