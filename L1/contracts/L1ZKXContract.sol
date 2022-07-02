// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.8.7;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
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
        uint256 timestamp_
    );
    event LogAssetListUpdated(uint256 ticker_, uint256 collateralId_);
    event LogAssetRemovedFromList(uint256 ticker_, uint256 collateralId_);
    event LogTokenContractAddressUpdated(
        uint256 ticker_,
        address tokenContractAddresses_
    );
    event LogDataFeedContractAddressUpdated(
        uint256 ticker_,
        address dataFeedContractAddress_
    );

    using SafeMath for uint256;

    // The StarkNet core contract.
    IStarknetCore starknetCore;
    AggregatorV3Interface internal usdcPriceFeed;
    AggregatorV3Interface internal ethPriceFeed;

    // Maps ticker to the token contract addresses
    mapping(uint256 => address) public tokenContractAddress;

    // Maps ticker with the asset ID
    mapping(uint256 => uint256) public assetID;

    // Maps the user address to the corresponding asset balance
    mapping(uint256 => mapping(uint256 => uint256)) public userBalance;

    // Maps L1 metamask account address to the l2 account contract address
    mapping(uint256 => uint256) public l2ContractAddress;

    // Maps ticker to the asset data feed contract address
    mapping(uint256 => address) public dataFeedContractAddress;

    // List of assets
    uint256[] public assetList;

    // Asset Contract address
    uint256 public zkxAssetContractAddress;

    // Withdrawal Request Contract Address
    uint256 public withdrawalRequestContractAddress;

    uint256 startGas;
    uint256 ethInUsd;
    uint256 usdcInUsd;
    uint256 amountInUsd;
    uint256 estimatedL1FeeInUsd;
    uint256 gasUsed;
    uint256 gasUsedInUsd;
    uint256 nodeOperatorsfee;

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
        uint256 zkxAssetContractAddress_,
        uint256 withdrawalRequestContractAddress_
    ) {
        starknetCore = starknetCore_;
        zkxAssetContractAddress = zkxAssetContractAddress_;
        withdrawalRequestContractAddress = withdrawalRequestContractAddress_;
        usdcPriceFeed = AggregatorV3Interface(usdcPriceFeedAddress);
        ethPriceFeed = AggregatorV3Interface(ethPriceFeedAddress);
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
        starknetCore.consumeMessageFromL2(zkxAssetContractAddress, payload);

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
        starknetCore.consumeMessageFromL2(zkxAssetContractAddress, payload);

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
     * @dev function to set data feed contract address
     * @param ticker_ - felt representation of the ticker
     * @param dataFeedContractAddress_ - address of the data feed contract
     **/
    function setDataFeedContractAddress(
        uint256 ticker_,
        address dataFeedContractAddress_
    ) public onlyRole(DEFAULT_ADMIN_ROLE) {
        // Update data feed contract address
        dataFeedContractAddress[ticker_] = dataFeedContractAddress_;
        emit LogDataFeedContractAddressUpdated(
            ticker_,
            dataFeedContractAddress_
        );
    }

    /**
     * Returns the latest price
     */
    function getLatestPrice(AggregatorV3Interface priceFeed)
        public
        view
        returns (int256)
    {
        (
            uint80 roundId,
            int256 price,
            uint256 startedAt,
            uint256 timeStamp,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();
        return price;
    }

    /**
     * @dev function to withdraw funds from an L2 Account contract
     * @param userL1Address_ - Users L1 wallet address
     * @param ticker_ - felt representation of the ticker
     * @param amount_ - The amount of tokens to be withdrawn
     * @param timestamp_ - The time at which withdrawal initiated
     * @param L1FeeAmount_ - Estimated Gas fee in L1
     * @param L1FeeTicker_ - Collateral used to pay L1 gas fee
     **/
    function withdraw(
        uint256 userL1Address_,
        uint256 ticker_,
        uint256 amount_,
        uint256 timestamp_,
        uint256 L1FeeAmount_,
        uint256 L1FeeTicker_
    ) public {
        startGas = gasleft();
        ethInUsd = uint256(getLatestPrice(ethPriceFeed));
        usdcInUsd = uint256(getLatestPrice(usdcPriceFeed));
        amountInUsd = amount_ * usdcInUsd;
        estimatedL1FeeInUsd = L1FeeAmount_ * usdcInUsd;

        uint256 userL2Address = l2ContractAddress[userL1Address_];
        uint256 collateralId = assetID[ticker_];
        uint256 L1FeecollateralId = assetID[L1FeeTicker_];

        // Construct withdrawal message payload.
        uint256[] memory withdrawal_payload = new uint256[](7);
        withdrawal_payload[0] = WITHDRAWAL_INDEX;
        withdrawal_payload[1] = userL1Address_;
        withdrawal_payload[2] = ticker_;
        withdrawal_payload[3] = amount_;
        withdrawal_payload[4] = timestamp_;
        withdrawal_payload[5] = L1FeeAmount_;
        withdrawal_payload[6] = L1FeeTicker_;

        // Consume the message from the StarkNet core contract.
        // This will revert the (Ethereum) transaction if the message does not exist.
        starknetCore.consumeMessageFromL2(userL2Address, withdrawal_payload);

        address tokenContract = tokenContractAddress[ticker_];
        gasUsed = startGas - gasleft();
        gasUsedInUsd = gasUsed * ethInUsd;
        if (gasUsedInUsd < estimatedL1FeeInUsd) {
            amountInUsd += (estimatedL1FeeInUsd - gasUsedInUsd);
        } else {
            amountInUsd -= (gasUsedInUsd - estimatedL1FeeInUsd);
        }
        amount_ = amountInUsd / usdcInUsd;
        nodeOperatorsfee = gasUsedInUsd / usdcInUsd;
        IERC20(tokenContract).transfer(
            address(uint160(userL1Address_)),
            amount_
        );
        IERC20(tokenContract).transfer(msg.sender, nodeOperatorsfee);

        // Construct update withdrawal request message payload.
        uint256[] memory updateWithdrawalRequestPayload = new uint256[](10);
        updateWithdrawalRequestPayload[0] = userL1Address_;
        updateWithdrawalRequestPayload[1] = userL2Address;
        updateWithdrawalRequestPayload[2] = ticker_;
        updateWithdrawalRequestPayload[3] = collateralId;
        updateWithdrawalRequestPayload[4] = amount_;
        updateWithdrawalRequestPayload[5] = timestamp_;
        updateWithdrawalRequestPayload[6] = uint256(
            uint160(address(msg.sender))
        );
        updateWithdrawalRequestPayload[7] = nodeOperatorsfee;
        updateWithdrawalRequestPayload[8] = L1FeeTicker_;
        updateWithdrawalRequestPayload[9] = L1FeecollateralId;

        // Send the message to the StarkNet core contract.
        starknetCore.sendMessageToL2(
            withdrawalRequestContractAddress,
            UPDATE_WITHDRAWAL_REQUEST_SELECTOR,
            updateWithdrawalRequestPayload
        );

        emit LogWithdrawal(
            address(uint160(userL1Address_)),
            ticker_,
            amount_,
            timestamp_
        );
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

        uint256 l2Recipient = l2ContractAddress[userL1Address_];

        // Construct the deposit message's payload.
        uint256[] memory payload = new uint256[](3);
        payload[0] = userL1Address_;
        payload[1] = amount_;
        payload[2] = collateralId_;

        // Send the message to the StarkNet core contract.
        starknetCore.sendMessageToL2(l2Recipient, DEPOSIT_SELECTOR, payload);
        emit LogDeposit(
            address(uint160(userL1Address_)),
            amount_,
            collateralId_,
            l2Recipient
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
        if (l2ContractAddress[uint256(uint160(address(msg.sender)))] == 0) {
            l2ContractAddress[
                uint256(uint160(address(msg.sender)))
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
        userBalance[uint256(uint160(address(msg.sender)))][
            collateralId
        ] = userBalance[uint256(uint160(address(msg.sender)))][collateralId]
            .add(amount_);
        depositToL2(
            uint256(uint160(address(msg.sender))),
            collateralId,
            amount_
        );
    }
}
