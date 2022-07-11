// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.8.7;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "./IStarknetCore.sol";
import "./Constants.sol";

/**
  Contract for L1 <-> L2 interaction between an L2 contracts and this
  L1 ZKX contract.
*/
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
    IStarknetCore starknetCore;

    // Maps ticker to the token contract addresses
    mapping(uint256 => address) public tokenContractAddress;

    // Maps ticker with the asset ID
    mapping(uint256 => uint256) public assetID;

    // Maps the user address to the corresponding asset balance
    mapping(uint256 => mapping(uint256 => uint256)) public userBalance;

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
        require(l2Address_ != 0, "L2_ADDRESS_OUT_OF_RANGE");
        require(l2Address_ < FIELD_PRIME, "L2_ADDRESS_OUT_OF_RANGE");
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
        public
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
        public
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
    function getAssetList() public view returns (uint256[] memory) {
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
    ) public onlyRole(DEFAULT_ADMIN_ROLE) {
        // Update token contract address
        tokenContractAddress[ticker_] = tokenContractAddress_;
        emit LogTokenContractAddressUpdated(ticker_, tokenContractAddress_);
    }

    /**
     * @dev function to set asset contract address
     * @param assetContractAddress_ - address of the asset contract
     **/
    function setAssetContractAddress(uint256 assetContractAddress_)
        public
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        assetContractAddress = assetContractAddress_;
    }

    /**
     * @dev function to set withdrawal request contract address
     * @param withdrawalRequestAddress_ - address of withdrawal request contract
     **/
    function setWithdrawalRequestAddress(uint256 withdrawalRequestAddress_)
        public
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
        uint256 collateralId_,
        uint256 amount_
    ) internal {
        require(
            amount_ <= userBalance[userL1Address_][collateralId_],
            "The user's balance is not large enough."
        );

        // Update the User balance.
        userBalance[userL1Address_][collateralId_] = userBalance[
            userL1Address_
        ][collateralId_].sub(amount_);

        uint256 userL2Address = l2ContractAddress[userL1Address_];

        // Construct the deposit message's payload.
        uint256[] memory depositPayload = new uint256[](3);
        depositPayload[0] = userL1Address_;
        depositPayload[1] = amount_;
        depositPayload[2] = collateralId_;

        // Send the message to the StarkNet core contract.
        starknetCore.sendMessageToL2(
            userL2Address,
            DEPOSIT_SELECTOR,
            depositPayload
        );

        emit LogDeposit(
            address(uint160(userL1Address_)),
            amount_,
            collateralId_,
            userL2Address
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
    ) public isValidL2Address(userL2Address_) {
        /**
         * If l2 contract address is not set, then it will be set for the corresponding
         * user's L1 wallet address
         */
        uint256 senderAsUint256 = uint256(uint160(address(msg.sender)));
        if (l2ContractAddress[senderAsUint256] == 0) {
            l2ContractAddress[
                senderAsUint256
            ] = userL2Address_;
        }

        address tokenContract = tokenContractAddress[ticker_];
        uint256 balance = IERC20(tokenContract).balanceOf(msg.sender);
        require(
            balance >= amount_,
            "User is trying to deposit more than he has"
        );

        IERC20(tokenContract).transferFrom(msg.sender, address(this), amount_);
        uint256 collateralId = assetID[ticker_];

        // Update the User balance.
        userBalance[senderAsUint256][
            collateralId
        ] = userBalance[senderAsUint256][collateralId]
            .add(amount_);
        depositToL2(
            senderAsUint256,
            collateralId,
            amount_
        );
    }

    /**
     * @dev function to deposit ETH to L1ZKX contract
     * @param userL2Address_ - The L2 account address of the user
     **/
    function depositEthToL1(
        uint256 userL2Address_
    ) payable public isValidL2Address(userL2Address_) {
        /**
         * If l2 contract address is not set, then it will be set for the corresponding
         * user's L1 wallet address
         */
        uint256 senderAsUint256 = uint256(uint160(address(msg.sender)));
        if (l2ContractAddress[senderAsUint256] == 0) {
            l2ContractAddress[
                senderAsUint256
            ] = userL2Address_;
        }

        uint256 collateralId = assetID[ETH_TICKER];

        // Update the User balance.
        userBalance[senderAsUint256][
            collateralId
        ] = userBalance[senderAsUint256][collateralId]
            .add(msg.value);
        depositToL2(
            senderAsUint256,
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
    ) public {
        require(msg.sender == address(uint160(userL1Address_)), "Sender is not withdraw recipient");
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
        IERC20(tokenContract).transfer(msg.sender, amount_);

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
    ) public {
        require(msg.sender == address(uint160(userL1Address_)), "Sender is not withdraw recipient");
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

        require(amount_ <= address(this).balance, "ETH to be transferred is more than the balance");
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
        public
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
        public
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        require(amount_ <= address(this).balance, "ETH to be transferred is more than the balance");
        recipient_.transfer(amount_);
    }
}
