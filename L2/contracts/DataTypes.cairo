%lang starknet

from starkware.cairo.common.uint256 import Uint256

// @notice struct to store details of markets
struct Market {
    id: felt,
    asset: felt,
    asset_collateral: felt,
    leverage: felt,
    is_tradable: felt,
    is_archived: felt,
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
    user_address: felt,
    sig_r: felt,
    sig_s: felt,
    liquidator_address: felt,
    order_id: felt,
    market_id: felt,
    direction: felt,
    price: felt,
    quantity: felt,
    leverage: felt,
    slippage: felt,
    order_type: felt,
    time_in_force: felt,
    post_only: felt,
    life_cycle: felt,
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
    order_id: felt,
    market_id: felt,
    direction: felt,
    price: felt,
    quantity: felt,
    leverage: felt,
    slippage: felt,
    order_type: felt,
    time_in_force: felt,
    post_only: felt,
    life_cycle: felt,
    liquidator_address: felt,
}

// @notice struct for storing the order data to Account Contract
struct PositionDetails {
    avg_execution_price: felt,
    position_size: felt,
    margin_amount: felt,
    borrowed_amount: felt,
    leverage: felt,
}

// Struct to be used for liquidation calls
struct PositionDetailsWithMarket {
    market_id: felt,
    direction: felt,
    avg_execution_price: felt,
    position_size: felt,
    margin_amount: felt,
    borrowed_amount: felt,
    leverage: felt,
}

// Struct to store the position that is to be Liquidated/Deleveraged
struct LiquidatablePosition {
    market_id: felt,
    direction: felt,
    amount_to_be_sold: felt,
    liquidatable: felt,
}

// @notice struct for sending the array of positions for ABR calculations
struct NetPositions {
    market_id: felt,
    position_size: felt,
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
    asset_id: felt,
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
    asset_id: felt,
    amount: felt,
    timestamp: felt,
    L1_fee_amount: felt,
    L1_fee_asset_id: felt,
}

// struct to store deposit payload information (for L1->L2 interaction) + other useful data
struct DepositData {
    user_L1_address: felt,
    user_L2_address: felt,
    asset_id: felt,
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

// Struct to store volume metadata
struct VolumeMetaData {
    season_id: felt,
    pair_id: felt,
    life_cycle: felt,  // open/close
}

// Struct to store trading season data
struct TradingSeason {
    start_block_number: felt,
    start_timestamp: felt,
    num_trading_days: felt,
}

// Struct to store multipliers used to calculate total reward to be split between traders
struct Multipliers {
    a_1: felt,
    a_2: felt,
    a_3: felt,
    a_4: felt,
}

// Struct to store constants used to calculate individual trader score
struct Constants {
    a: felt,
    b: felt,
    c: felt,
    z: felt,
    e: felt,
}

// Struct to store details of reward tokens
struct RewardToken {
    token_id: felt,  // L1 ERC20 contract address
    no_of_tokens: Uint256,
}

// Struct to store hightide metadata
struct HighTideMetaData {
    pair_id: felt,  // supported market
    status: felt,  // either initialized (by token lister) or active (by zkx, if funds or locked in the pool)
    season_id: felt,  // season in which hightide to be activated
    token_lister_address: felt,  // L2 address of token lister
    is_burnable: felt,  // 0 - return to token lister, 1 - burn tokens
    liquidity_pool_address: felt,  // contract address of liquidity pool associated with hightide
}

// Struct to store high-tide factors
struct HighTideFactors {
    x_1: felt,
    x_2: felt,
    x_3: felt,
    x_4: felt,
}

// Struct to store Trader's stats
struct TraderStats {
    trader_address: felt,
    fee_64x61: felt,
    order_volume_64x61: felt,
    life_cycle: felt,  // 1 for open order, 2 for close order
    pnl_64x61: felt,
    margin_amount_64x61: felt,
}

// Struct to pass xp values to L2
struct XpValues {
    user_address: felt,
    final_xp_value: felt,
}

struct LeaderboardStat {
    user_address: felt,
    reward: felt,
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
