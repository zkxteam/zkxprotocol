%lang starknet

// @notice struct to store details of markets
struct Market {
    asset: felt,
    assetCollateral: felt,
    leverage: felt,
    tradable: felt,
    archived: felt,
    ttl: felt,
    tick_size: felt,
    step_size: felt,
    minimum_order_size: felt,
    minimum_leverage: felt,
    maximum_leverage: felt,
    currently_allowed_leverage: felt,
    maintenance_margin_fraction: felt,
    initial_margin_fraction: felt,
    incremental_initial_margin_fraction: felt,
    incremental_position_size: felt,
    baseline_position_size: felt,
    maximum_position_size: felt,
}

// @notice struct to store details of assets
struct Asset {
    id: felt,
    asset_version: felt,
    short_name: felt,
    is_tradable: felt,
    is_collateral: felt,
    token_decimal: felt,
}

// @notice Struct to store base fee percentage for each tier for maker and taker
struct BaseFee {
    numberOfTokens: felt,
    makerFee: felt,
    takerFee: felt,
}

// @notice Struct to store discount percentage for each tier
struct Discount {
    numberOfTokens: felt,
    discount: felt,
}

// Struct to pass orders+signatures in a batch in the execute_batch fn
struct MultipleOrder {
    pub_key: felt,
    sig_r: felt,
    sig_s: felt,
    orderID: felt,
    assetID: felt,
    collateralID: felt,
    price: felt,
    stopPrice: felt,
    orderType: felt,
    positionSize: felt,
    direction: felt,
    closeOrder: felt,
    leverage: felt,
    liquidatorAddress: felt,
    parentOrder: felt,
    side: felt,
}

// @notice struct to pass price data to the contract
struct PriceData {
    assetID: felt,
    collateralID: felt,
    assetPrice: felt,
    collateralPrice: felt,
}

// @notice struct for passing the order request to Account Contract
struct OrderRequest {
    orderID: felt,
    assetID: felt,
    collateralID: felt,
    price: felt,
    stopPrice: felt,
    orderType: felt,
    positionSize: felt,
    direction: felt,
    closeOrder: felt,
    leverage: felt,
    liquidatorAddress: felt,
    parentOrder: felt,
}

// @notice struct for storing the order data to Account Contract
struct OrderDetails {
    assetID: felt,
    collateralID: felt,
    price: felt,
    executionPrice: felt,
    positionSize: felt,
    orderType: felt,
    direction: felt,
    portionExecuted: felt,
    status: felt,
    marginAmount: felt,
    borrowedAmount: felt,
    leverage: felt,
}

// Struct for passing signature to Account Contract
struct Signature {
    r_value: felt,
    s_value: felt,
}

// Struct for Withdrawal Request
struct WithdrawalRequest {
    user_l1_address: felt,
    user_l2_address: felt,
    ticker: felt,
    amount: felt,
}

// Struct to pass the transactions to the contract
struct Message {
    sender: felt,
    to: felt,
    selector: felt,
    calldata: felt*,
    calldata_size: felt,
    nonce: felt,
}

// status 0: initiated
// status 1: partial
// status 2: executed
// status 3: close partial
// status 4: close
// status 5: toBeDeleveraged
// status 6: toBeLiquidated
// status 7: fullyLiquidated
struct OrderDetailsWithIDs {
    orderID: felt,
    assetID: felt,
    collateralID: felt,
    price: felt,
    executionPrice: felt,
    positionSize: felt,
    orderType: felt,
    direction: felt,
    portionExecuted: felt,
    status: felt,
    marginAmount: felt,
    borrowedAmount: felt,
}

// Struct to store collateral balances
struct CollateralBalance {
    assetID: felt,
    balance: felt,
}

// Struct to store withdrawal details
// status 0: initiated
// status 1: withdrawal succcessful
struct WithdrawalHistory {
    request_id: felt,
    collateral_id: felt,
    amount: felt,
    timestamp: felt,
    node_operator_L2_address: felt,
    fee: felt,
    status: felt,
}

// Struct for hashing withdrawal request
struct WithdrawalRequestForHashing {
    request_id: felt,
    collateral_id: felt,
    amount: felt,
}

// Struct to store Market price
struct MarketPrice {
    asset_id: felt,
    collateral_id: felt,
    timestamp: felt,
    price: felt,
}

// Struct for message to consume for quoting fee in L1
struct QuoteL1Message {
    user_l1_address: felt,
    ticker: felt,
    amount: felt,
    timestamp: felt,
    L1_fee_amount: felt,
    L1_fee_ticker: felt,
}

struct CoreFunctionCall {
    index: felt,
    version: felt,
    nonce: felt,
    function_selector: felt,
    calldata_len: felt,
    calldata: felt*,
}

struct CoreFunction {
    index: felt,
    version: felt,
    function_selector: felt,
}
// struct to store deposit payload information (for L1->L2 interaction) + other useful data
struct DepositData {
    user_L1_address: felt,
    user_L2_address: felt,
    ticker: felt,
    amount: felt,
    nonce: felt,
    message_hash: felt,
    timestamp: felt,
}

// Struct to store Collateral price
struct CollateralPrice {
    timestamp: felt,
    price_in_usd: felt,
}
