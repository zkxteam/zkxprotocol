%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math import abs_value, assert_le, assert_lt, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import emit_event

from contracts.Constants import (
    AccountRegistry_INDEX,
    Asset_INDEX,
    BUY,
    CLOSE,
    DELEVERAGING_ORDER,
    FeeBalance_INDEX,
    FoK,
    Holding_INDEX,
    InsuranceFund_INDEX,
    LIMIT_ORDER,
    Liquidate_INDEX,
    LIQUIDATION_ORDER,
    LiquidityFund_INDEX,
    LONG,
    MAKER,
    Market_INDEX,
    MARKET_ORDER,
    MarketPrices_INDEX,
    OPEN,
    SELL,
    TAKER,
    TradingFees_INDEX,
    TradingStats_INDEX,
)
from contracts.DataTypes import (
    Asset,
    Market,
    MultipleOrder,
    OrderRequest,
    PositionDetails,
    PositionDetailsForRiskManagement,
    Signature,
    TraderStats,
)
from contracts.interfaces.IAccountManager import IAccountManager
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IFeeBalance import IFeeBalance
from contracts.interfaces.IHolding import IHolding
from contracts.interfaces.IInsuranceFund import IInsuranceFund
from contracts.interfaces.ILiquidate import ILiquidate
from contracts.interfaces.ILiquidityFund import ILiquidityFund
from contracts.interfaces.IMarketPrices import IMarketPrices
from contracts.interfaces.IMarkets import IMarkets
from contracts.interfaces.ITradingStats import ITradingStats
from contracts.interfaces.ITradingFees import ITradingFees
from contracts.libraries.CommonLibrary import CommonLib
from contracts.Math_64x61 import (
    Math64x61_add,
    Math64x61_assert_le,
    Math64x61_div,
    Math64x61_is_equal,
    Math64x61_is_le,
    Math64x61_mul,
    Math64x61_ONE,
    Math64x61_sub,
)

// ////////////
// Constants //
// ////////////

const LEVERAGE_ONE = 2305843009213693952;
const NEGATIVE_ONE = 3618502788666131213697322783095070105623107215331596699970786213126658326529;
const FIFTEEN_PERCENTAGE = 34587645138205409280;
const HUNDRED = 230584300921369395200;
const TWO = 4611686018427387904;

// //////////
// Storage //
// //////////

// Stores if a batch id is executed
@storage_var
func batch_id_status(batch_id: felt) -> (res: felt) {
}

// Stores size locked for a user if order is SELL
@storage_var
func position_size_locked_per_user(
    batch_id: felt, user_address: felt, market_id: felt, direction: felt
) -> (res: felt) {
}

// //////////////
// Constructor //
// //////////////

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    return ();
}

// ///////
// View //
// ///////

@view
func get_batch_id_status{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    batch_id_: felt
) -> (status: felt) {
    alloc_locals;

    let (status: felt) = batch_id_status.read(batch_id=batch_id_);
    return (status,);
}

// ///////////
// External //
// ///////////

// @notice Function to execute multiple orders in a batch
// @param quantity_locked_ - Size of the order to be executed
// @param market_id_ - Market id of the batch
// @param oracle_price_ - Average of the oracle prices sent by ZKX Nodes
// @param request_list_len - No of orders in the batch
// @param request_list - The batch of the orders
@external
func execute_batch{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*
}(
    batch_id_: felt,
    quantity_locked_: felt,
    market_id_: felt,
    oracle_price_: felt,
    request_list_len: felt,
    request_list: MultipleOrder*,
) -> () {
    alloc_locals;

    // Get all the addresses from the auth registry
    let (
        account_registry_address: felt,
        asset_address: felt,
        holding_address: felt,
        trading_fees_address: felt,
        fees_balance_address: felt,
        liquidity_fund_address: felt,
        insurance_fund_address: felt,
        liquidate_address: felt,
        trading_stats_address: felt,
        market_address: felt,
        market_prices_address: felt,
    ) = get_registry_addresses();

    // get collateral id
    let (asset_id: felt, collateral_id: felt) = IMarkets.get_asset_collateral_from_market(
        contract_address=market_address, market_id_=market_id_
    );

    // Get Asset to fetch number of token decimals of an asset
    let (asset: Asset) = IAsset.get_asset(contract_address=asset_address, id=asset_id);

    // Get collateral to fetch number of token decimals of a collateral
    let (collateral: Asset) = IAsset.get_asset(contract_address=asset_address, id=collateral_id);

    // Initialize trader_stats_list
    let (trader_stats_list: TraderStats*) = alloc();

    // Get the market details
    let (market: Market) = IMarkets.get_market(
        contract_address=market_address, market_id_=market_id_
    );

    with_attr error_message("0509: {market_id_}") {
        assert_not_zero(market.is_tradable);
    }

    with_attr error_message("0522: {market_id_}") {
        assert_not_zero(quantity_locked_);
    }

    let (execution_sizes: felt*) = alloc();

    adjust_quantity_locked(
        batch_id_=batch_id_,
        asset_token_decimal_=asset.token_decimal,
        request_list_len_=request_list_len,
        request_list_=request_list,
        quantity_locked_=quantity_locked_,
        execution_sizes_=execution_sizes,
    );

    // Recursively loop through the orders in the batch
    let (taker_execution_price: felt, open_interest: felt) = check_and_execute(
        batch_id_=batch_id_,
        market_id_=market_id_,
        collateral_id_=collateral_id,
        asset_token_decimal_=asset.token_decimal,
        collateral_token_decimal_=collateral.token_decimal,
        orders_len_=request_list_len,
        request_list_len_=request_list_len,
        request_list_=request_list,
        quantity_executed_=0,
        account_registry_address_=account_registry_address,
        holding_address_=holding_address,
        trading_fees_address_=trading_fees_address,
        fees_balance_address_=fees_balance_address,
        liquidate_address_=liquidate_address,
        liquidity_fund_address_=liquidity_fund_address,
        insurance_fund_address_=insurance_fund_address,
        max_leverage_=market.currently_allowed_leverage,
        min_quantity_=market.minimum_order_size,
        maker1_direction_=[request_list].direction,
        maker1_side_=[request_list].side,
        trader_stats_list_=trader_stats_list,
        total_order_volume_=0,
        taker_execution_price=0,
        open_interest_=0,
        oracle_price_=oracle_price_,
        execution_sizes_=execution_sizes,
    );

    // Get Market price for the corresponding market Id
    let (market_price: felt) = IMarketPrices.get_market_price(
        contract_address=market_prices_address, id=market_id_
    );

    // update market price
    if (market_price == 0) {
        IMarketPrices.update_market_price(
            contract_address=market_prices_address, id=market_id_, price=oracle_price_
        );
        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Record TradingStats
    ITradingStats.record_trade_batch_stats(
        contract_address=trading_stats_address,
        market_id_=market_id_,
        execution_price_64x61_=taker_execution_price,
        request_list_len=request_list_len,
        request_list=request_list,
        trader_stats_list_len=request_list_len,
        trader_stats_list=trader_stats_list,
        executed_sizes_list_len=request_list_len,
        executed_sizes_list=execution_sizes,
        open_interest_=open_interest,
    );

    // Change the status of the batch to TRUE
    batch_id_status.write(batch_id=batch_id_, value=TRUE);

    return ();
}

// ///////////
// Internal //
// ///////////

// @notice Internal function to calculate the amount that must be executed for an order
// @param asset_token_decimal_ - Number of decimals for the asset
// @param request_ - An order request
// @param quantity_remainging - Max quantity that can be executed for that order
// @param execution_sizes_ - Array of the calculated execution sizes
// @returns quantity_to_execute_final - Calculated quantity to execute
func get_quantity_to_execute{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    batch_id_: felt, asset_token_decimal_: felt, request_: MultipleOrder, quantity_remaining_: felt
) -> (quantity_to_execute_final: felt) {
    alloc_locals;
    local quantity_to_execute;
    local quantity_to_execute_final;

    // Get the portion executed of the order
    let (order_portion_executed: felt) = IAccountManager.get_portion_executed(
        contract_address=request_.user_address, order_id_=request_.order_id
    );

    // Get min of remaining quantity and the order quantity
    let (executable_quantity: felt) = Math64x61_sub(request_.quantity, order_portion_executed);
    let (cmp_res) = Math64x61_is_le(quantity_remaining_, executable_quantity, asset_token_decimal_);

    // If yes, make the quantity_to_execute to be quantity_remaining
    // i.e Partial order
    if (cmp_res == TRUE) {
        assert quantity_to_execute = quantity_remaining_;
    } else {
        assert quantity_to_execute = executable_quantity;
    }

    local order_id;
    local quantity_remaining;
    assert order_id = request_.order_id;
    assert quantity_remaining = quantity_remaining_;

    // If it's a sell order, calculate the amount that can be executed
    if (request_.side == SELL) {
        // Get the order size already locked for the current batch
        let (current_batch_locked_size) = position_size_locked_per_user.read(
            batch_id_, request_.user_address, request_.market_id, request_.direction
        );
        // Get position details
        let (position_details: PositionDetails) = IAccountManager.get_position_data(
            contract_address=request_.user_address,
            market_id_=request_.market_id,
            direction_=request_.direction,
        );

        let (remaining_position_size) = Math64x61_sub(
            position_details.position_size, current_batch_locked_size
        );

        let (cmp_res) = Math64x61_is_le(
            quantity_to_execute, remaining_position_size, asset_token_decimal_
        );

        if (cmp_res == FALSE) {
            quantity_to_execute_final = remaining_position_size;
        } else {
            quantity_to_execute_final = quantity_to_execute;
        }

        // Update position size locked for the user in current batch
        let (current_batch_locked_size_new) = Math64x61_add(
            current_batch_locked_size, quantity_to_execute_final
        );
        position_size_locked_per_user.write(
            batch_id_,
            request_.user_address,
            request_.market_id,
            request_.direction,
            current_batch_locked_size_new,
        );

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        quantity_to_execute_final = quantity_to_execute;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    return (quantity_to_execute_final,);
}

// @notice Internal function to recurse through maker orders and
// calculate the size that must be executed for each
// @param asset_token_decimal_ - Number of decimals for the asset
// @param request_list_len_ - Length of the requests list
// @param request_list_ - Request list of orders
// @param execution_sizes_ - Array of the calculated execution sizes
// @param taker_locked_quantity_ - Adjsut taker execution Size
// @param quantity_executed_ - Quantity that has been locked so far on maker side
// @param iterator_ - Iterator for the execution_sizes_ array
func get_maker_sizes{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    batch_id_: felt,
    asset_token_decimal_: felt,
    request_list_len_: felt,
    request_list_: MultipleOrder*,
    execution_sizes_: felt*,
    taker_locked_quantity_: felt,
    quantity_executed_: felt,
    iterator_: felt,
) -> (maker_quantity_to_execute: felt) {
    // Reached the end of maker orders
    if (request_list_len_ == 1) {
        return (quantity_executed_,);
    }
    // Find quantity left to be executed
    let (quantity_remaining) = Math64x61_sub(taker_locked_quantity_, quantity_executed_);
    // Find quantity that needs to be executed for the current order
    let (quantity_to_execute) = get_quantity_to_execute(
        batch_id_=batch_id_,
        asset_token_decimal_=asset_token_decimal_,
        request_=[request_list_],
        quantity_remaining_=quantity_remaining,
    );

    // Store it in the array
    assert execution_sizes_[iterator_] = quantity_to_execute;

    // New quantity executed
    let (quantity_executed_new) = Math64x61_add(quantity_to_execute, quantity_executed_);
    return get_maker_sizes(
        batch_id_=batch_id_,
        asset_token_decimal_=asset_token_decimal_,
        request_list_len_=request_list_len_ - 1,
        request_list_=request_list_ + MultipleOrder.SIZE,
        execution_sizes_=execution_sizes_,
        taker_locked_quantity_=taker_locked_quantity_,
        quantity_executed_=quantity_executed_new,
        iterator_=iterator_ + 1,
    );
}

// @notice Internal function to adjust and calculate the quantity locked and execution sizes
// @param asset_token_decimal_ - Number of decimals for the asset
// @param request_list_len_ - Length of the requests list
// @param request_list_ - Request list of orders
// @param quantity_locked_ - Original quantity lokcked of the batch
// @param execution_sizes_ - Array of the calculated execution sizes
func adjust_quantity_locked{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    batch_id_: felt,
    asset_token_decimal_: felt,
    request_list_len_: felt,
    request_list_: MultipleOrder*,
    quantity_locked_: felt,
    execution_sizes_: felt*,
) -> () {
    // Get the index of the Taker order
    let last_index = request_list_len_ - 1;

    // Adjust the quantity to execute on the taker side
    let (taker_quantity_to_execute) = get_quantity_to_execute(
        batch_id_=batch_id_,
        asset_token_decimal_=asset_token_decimal_,
        request_=request_list_[last_index],
        quantity_remaining_=quantity_locked_,
    );

    with_attr error_message("0523: {quantity_locked_}") {
        assert_not_zero(taker_quantity_to_execute);
    }

    // Adjust the quantity to execute on the maker side and fill the execution_sizes_ array
    let (maker_quantity_to_execute) = get_maker_sizes(
        batch_id_=batch_id_,
        asset_token_decimal_=asset_token_decimal_,
        request_list_len_=request_list_len_,
        request_list_=request_list_,
        execution_sizes_=execution_sizes_,
        taker_locked_quantity_=taker_quantity_to_execute,
        quantity_executed_=0,
        iterator_=0,
    );

    with_attr error_message("0524: {quantity_locked_}") {
        assert_not_zero(maker_quantity_to_execute);
    }

    // Store the new adjusted execution size of taker order
    assert execution_sizes_[last_index] = maker_quantity_to_execute;

    return ();
}

// @notice Internal function to check to check the slippage of a market order
// @param order_id_ - Order ID of the order
// @param slippage_ - Slippage % of the order
// @param oracle_price_ - Oracle price of the batch
// @param execution_price_ - Execution price of the order
func check_within_slippage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_id_: felt,
    slippage_: felt,
    oracle_price_: felt,
    execution_price_: felt,
    direction_: felt,
    side_: felt,
    collateral_token_decimal_: felt,
) {
    // To remove
    alloc_locals;
    with_attr error_message("0521: {order_id_} {slippage_}") {
        assert_lt(0, slippage_);
        assert_le(slippage_, FIFTEEN_PERCENTAGE);
    }

    let (percentage) = Math64x61_div(slippage_, HUNDRED);
    let (threshold) = Math64x61_mul(percentage, oracle_price_);

    let (lower_limit: felt) = Math64x61_sub(oracle_price_, threshold);
    let (upper_limit: felt) = Math64x61_add(oracle_price_, threshold);

    if (direction_ == side_) {
        with_attr error_message("0506: {order_id_} {execution_price_}") {
            Math64x61_assert_le(execution_price_, upper_limit, collateral_token_decimal_);
        }
    } else {
        with_attr error_message("0506: {order_id_} {execution_price_}") {
            Math64x61_assert_le(lower_limit, execution_price_, collateral_token_decimal_);
        }
    }

    return ();
}

// @notice Internal function to check if the execution_price of a limit order is valid (TAKER)
// @param order_id_ - Order ID of the order
// @param price_ - Limit price of the order
// @param execution_price_ - Execution price of the order
// @param side_ - Side of the order BUY/SELL
// @param collateral_token_decimal_ - Number of decimals for the collateral
func check_limit_price{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_id_: felt,
    price_: felt,
    execution_price_: felt,
    direction_: felt,
    side_: felt,
    collateral_token_decimal_: felt,
) {
    alloc_locals;

    if (direction_ == LONG) {
        // if it's a long order
        if (side_ == BUY) {
            // if it's a buy order
            with_attr error_message("0508: {order_id_} {execution_price_}") {
                Math64x61_assert_le(execution_price_, price_, collateral_token_decimal_);
            }
        } else {
            // if it's a sell order
            with_attr error_message("0507: {order_id_} {execution_price_}") {
                Math64x61_assert_le(price_, execution_price_, collateral_token_decimal_);
            }
        }
        tempvar range_check_ptr = range_check_ptr;
    } else {
        // if it's a short order
        if (side_ == BUY) {
            // if it's a buy order
            with_attr error_message("0507: {order_id_} {execution_price_}") {
                Math64x61_assert_le(price_, execution_price_, collateral_token_decimal_);
            }
        } else {
            // if it's a sell order
            with_attr error_message("0508: {order_id_} {execution_price_}") {
                Math64x61_assert_le(execution_price_, price_, collateral_token_decimal_);
            }
        }
        tempvar range_check_ptr = range_check_ptr;
    }

    return ();
}

// @notice Internal function to retrieve contract addresses from the Auth Registry
// @returns account_registry_address - Address of the Account Registry contract
// @returns asset_address - Address of the Asset contract
// @returns holding_address - Address of the Holding contract
// @returns trading_fees_address - Address of the Trading contract
// @returns fees_balance_address - Address of the Fee Balance contract
// @returns liquidity_fund_address - Address of the Liquidity Fund contract
// @returns insurance_fund_address - Address of the Insurance Fund contract
// @returns liquidate_address - Address of the Liquidate contract
// @returns trading_stats_address - Address of the Trading stats contract
// @returns market_address - Address of the Market contract
// @returns market_prices_address - Address of the Market Prices contract
func get_registry_addresses{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    account_registry_address: felt,
    asset_address: felt,
    holding_address: felt,
    trading_fees_address: felt,
    fees_balance_address: felt,
    liquidity_fund_address: felt,
    insurance_fund_address: felt,
    liquidate_address: felt,
    trading_stats_address: felt,
    market_address: felt,
    market_prices_address: felt,
) {
    // Read the registry and version
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get account Registry address
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    );

    // Get Asset contract address
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );

    // Get holding address
    let (holding_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Holding_INDEX, version=version
    );

    // Get Trading fees address
    let (trading_fees_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=TradingFees_INDEX, version=version
    );

    // Get Fee balance address
    let (fees_balance_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=FeeBalance_INDEX, version=version
    );

    // Get Liquidate address
    let (liquidate_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Liquidate_INDEX, version=version
    );

    // Get Liquidity Fund address
    let (liquidity_fund_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=LiquidityFund_INDEX, version=version
    );

    // Get Insurance fund address
    let (insurance_fund_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=InsuranceFund_INDEX, version=version
    );

    // Get Trading stats address
    let (trading_stats_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=TradingStats_INDEX, version=version
    );

    // Get Market address
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get Market address
    let (market_prices_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=MarketPrices_INDEX, version=version
    );

    return (
        account_registry_address,
        asset_address,
        holding_address,
        trading_fees_address,
        fees_balance_address,
        liquidity_fund_address,
        insurance_fund_address,
        liquidate_address,
        trading_stats_address,
        market_address,
        market_prices_address,
    );
}

// @notice Intenal function that processes open orders
// @param order_ - Order request
// @param execution_price_ - The price at which it got matched
// @param order_size_ - The size of the asset that got matched
// @param market_id_ - The market ID of the batch
// @param collateral_id_ - Collateral_id of all the orders in the batch
// @param collateral_token_decimal_ - No.of token decimals of collateral
// @param liquidity_fund_address_ - Address of the Liquidity contract
// @param liquidate_address_ - Address of the Liquidate contract
// @param holding_address_ - Address of the Holding contract
// @param trader_stats_list_ - traders fee list
// @returns average_execution_price_open - Average Execution Price for the order
// @returns margin_amount_open - Margin amount for the order
// @returns borrowed_amount_open - Borrowed amount for the order
func process_open_orders{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_: MultipleOrder,
    execution_price_: felt,
    order_size_: felt,
    market_id_: felt,
    collateral_id_: felt,
    collateral_token_decimal_: felt,
    liquidity_fund_address_: felt,
    liquidate_address_: felt,
    holding_address_: felt,
    trading_fees_address_: felt,
    fees_balance_address_: felt,
    trader_stats_list_: TraderStats*,
    side_: felt,
) -> (
    average_execution_price_open: felt,
    margin_amount_open: felt,
    borrowed_amount_open: felt,
    trading_fee: felt,
    margin_lock_amount: felt,
) {
    alloc_locals;

    local margin_amount_open;
    local borrowed_amount_open;
    local average_execution_price_open;
    local user_available_balance;
    local trading_fee;
    local order_id;

    // Get the fees from Trading Fee contract
    let (fees_rate, base_fee_tier, discount_tier) = ITradingFees.get_discounted_fee_rate_for_user(
        contract_address=trading_fees_address_, address_=order_.user_address, side_=side_
    );

    // Get position details
    let (position_details: PositionDetails) = IAccountManager.get_position_data(
        contract_address=order_.user_address, market_id_=market_id_, direction_=order_.direction
    );
    let margin_amount = position_details.margin_amount;
    let borrowed_amount = position_details.borrowed_amount;

    // calculate avg execution price
    if (position_details.position_size == 0) {
        assert average_execution_price_open = execution_price_;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        let (portion_executed_value) = Math64x61_mul(
            position_details.position_size, position_details.avg_execution_price
        );
        let (current_order_value) = Math64x61_mul(order_size_, execution_price_);
        let (cumulative_order_value) = Math64x61_add(portion_executed_value, current_order_value);
        let (cumulative_order_size) = Math64x61_add(position_details.position_size, order_size_);
        let (cumulative_price) = Math64x61_div(cumulative_order_value, cumulative_order_size);

        assert average_execution_price_open = cumulative_price;
        tempvar range_check_ptr = range_check_ptr;
    }

    let (leveraged_order_value) = Math64x61_mul(order_size_, execution_price_);
    let (margin_order_value) = Math64x61_div(leveraged_order_value, order_.leverage);
    let (amount_to_be_borrowed_felt) = Math64x61_sub(leveraged_order_value, margin_order_value);
    tempvar amount_to_be_borrowed = amount_to_be_borrowed_felt;

    // Calculate borrowed and margin amounts to be stored in account contract
    let (margin_amount_open_felt) = Math64x61_add(margin_amount, margin_order_value);
    let (borrowed_amount_open_felt) = Math64x61_add(borrowed_amount, amount_to_be_borrowed);
    assert margin_amount_open = margin_amount_open_felt;
    assert borrowed_amount_open = borrowed_amount_open_felt;

    // Calculate the fees for the order
    let (fees) = Math64x61_mul(fees_rate, leveraged_order_value);
    let (trading_fee) = Math64x61_mul(fees, NEGATIVE_ONE);

    // Check if the position can be opened
    let (available_margin) = ILiquidate.check_for_risk(
        contract_address=liquidate_address_,
        order_=order_,
        size=order_size_,
        execution_price_=execution_price_,
        margin_amount_=margin_order_value,
    );

    // Setting local values to be used in error message
    assert user_available_balance = available_margin;
    assert order_id = order_.order_id;

    // User must be able to pay the amount
    with_attr error_message("0501: {order_id} {user_available_balance}") {
        Math64x61_assert_le(fees, user_available_balance, collateral_token_decimal_);
    }

    if (is_le(fees, 0) == 0) {
        // Deduct the fee from account contract
        IAccountManager.transfer_from(
            contract_address=order_.user_address,
            asset_id_=collateral_id_,
            market_id_=0,
            amount_=fees,
            invoked_for_='fee',
        );

        // Update the fees to be paid by user in fee balance contract
        IFeeBalance.update_fee_mapping(
            contract_address=fees_balance_address_,
            address=order_.user_address,
            assetID_=collateral_id_,
            fee_to_add=fees,
        );
        tempvar range_check_ptr = range_check_ptr;
        tempvar syscall_ptr = syscall_ptr;
    } else {
        tempvar range_check_ptr = range_check_ptr;
        tempvar syscall_ptr = syscall_ptr;
    }

    let (order_volume_64x61) = Math64x61_mul(order_size_, execution_price_);

    // Update Trader stats
    let element: TraderStats = TraderStats(
        trader_address=order_.user_address,
        fee_64x61=fees,
        order_volume_64x61=order_volume_64x61,
        side=BUY,
        pnl_64x61=0,
        margin_amount_64x61=0,
    );
    assert [trader_stats_list_] = element;

    // Deduct the amount from liquidity funds if order is leveraged
    let is_non_leveraged = is_le(order_.leverage, Math64x61_ONE);

    if (is_non_leveraged == FALSE) {
        ILiquidityFund.withdraw(
            contract_address=liquidity_fund_address_,
            asset_id_=collateral_id_,
            amount=amount_to_be_borrowed,
            position_id_=order_.order_id,
        );
        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Deposit the funds taken from the user and liquidity fund
    IHolding.deposit(
        contract_address=holding_address_, asset_id_=collateral_id_, amount_=leveraged_order_value
    );

    return (
        average_execution_price_open,
        margin_amount_open,
        borrowed_amount_open,
        trading_fee,
        margin_order_value,
    );
}

// @notice Intenal function that processes close orders including Liquidation & Deleveraging
// @param order_ - Order request
// @param execution_price_ - The price at which it got matched
// @param order_size_ - The size of the asset that got matched
// @param market_id_ - The market ID of the batch
// @param collateral_id_ - Collateral_id of all the orders in the batch
// @param collateral_token_decimal_ - No.of token decimals of collateral
// @param liquidity_fund_address_ - Address of the Liquidity contract
// @param insurance_fund_address - Address of the Insurance Fund contract
// @param holding_address_ - Address of the Holding contract
// @param trader_stats_list_ - traders fee list
// @returns average_execution_price_open - Average Execution Price for the order
// @returns margin_amount_open - Margin amount for the order
// @returns borrowed_amount_open - Borrowed amount for the order
func process_close_orders{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_: MultipleOrder,
    execution_price_: felt,
    order_size_: felt,
    market_id_: felt,
    collateral_id_: felt,
    collateral_token_decimal_: felt,
    liquidity_fund_address_: felt,
    insurance_fund_address_: felt,
    holding_address_: felt,
    trader_stats_list_: TraderStats*,
) -> (
    margin_amount_close: felt,
    borrowed_amount_close: felt,
    average_execution_price_close: felt,
    realized_pnl: felt,
    margin_unlock_amount: felt,
) {
    alloc_locals;

    local margin_amount_close;
    local borrowed_amount_close;
    local average_execution_price_close;
    local realized_pnl;
    // To be passed as arguments to error_message
    local order_id;
    local order_direction;
    assert order_id = order_.order_id;
    assert order_direction = order_.direction;

    // Get order details
    let (current_position: PositionDetails) = IAccountManager.get_position_data(
        contract_address=order_.user_address, market_id_=market_id_, direction_=order_.direction
    );

    let margin_amount = current_position.margin_amount;
    let borrowed_amount = current_position.borrowed_amount;
    average_execution_price_close = current_position.avg_execution_price;

    local diff;
    local actual_execution_price;
    local margin_plus_pnl;

    // current order is a long order
    if (order_.direction == LONG) {
        assert actual_execution_price = execution_price_;
        let (diff_felt) = Math64x61_sub(execution_price_, current_position.avg_execution_price);
        assert diff = diff_felt;
    } else {
        let (diff_felt) = Math64x61_sub(current_position.avg_execution_price, execution_price_);
        assert diff = diff_felt;
        let (actual_exexution_price_felt) = Math64x61_add(
            current_position.avg_execution_price, diff
        );

        assert actual_execution_price = actual_exexution_price_felt;
    }

    // Total value of the asset at current price
    let (leveraged_amount_out) = Math64x61_mul(order_size_, actual_execution_price);

    // Calculate the amount that needs to be returned to liquidity fund
    let (ratio_of_position) = Math64x61_div(order_size_, current_position.position_size);
    let (borrowed_amount_to_be_returned) = Math64x61_mul(borrowed_amount, ratio_of_position);
    let (local margin_amount_to_be_reduced) = Math64x61_mul(margin_amount, ratio_of_position);
    local margin_amount_open_64x61;

    // Calculate pnl and net account value
    let (pnl) = Math64x61_mul(order_size_, diff);
    let (margin_plus_pnl_felt) = Math64x61_add(margin_amount_to_be_reduced, pnl);
    assert margin_plus_pnl = margin_plus_pnl_felt;


    // Calculate new values for margin and borrowed amounts
    if (order_.order_type == DELEVERAGING_ORDER) {
        // In delevereaging, we only reduce borrowed field
        let (borrowed_amount_close_felt) = Math64x61_sub(borrowed_amount, leveraged_amount_out);
        assert borrowed_amount_close = borrowed_amount_close_felt;

        // New margin amount of the position
        margin_amount_close = margin_amount;
        margin_amount_open_64x61 = 0;

        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        // New borrowed amount of the position
        let (borrowed_amount_close_felt) = Math64x61_sub(
            borrowed_amount, borrowed_amount_to_be_returned
        );
        assert borrowed_amount_close = borrowed_amount_close_felt;

        // New margin amount of the position
        let (margin_amount_close_felt) = Math64x61_sub(margin_amount, margin_amount_to_be_reduced);
        assert margin_amount_close = margin_amount_close_felt;
        margin_amount_open_64x61 = margin_amount_to_be_reduced;

        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    let (order_volume_64x61) = Math64x61_mul(order_size_, execution_price_);

    // Update trader stats.
    // If close order is a deleveraging order, margin won't be reduced. So, we will record 0.
    // Else, we will record margin_to_be_reduced
    let element: TraderStats = TraderStats(
        trader_address=order_.user_address,
        fee_64x61=0,
        order_volume_64x61=order_volume_64x61,
        side=SELL,
        pnl_64x61=pnl,
        margin_amount_64x61=margin_amount_open_64x61,
    );
    assert [trader_stats_list_] = element;

    // Deduct funds from holding contract
    if (is_le(0, leveraged_amount_out) == TRUE) {
        IHolding.withdraw(
            contract_address=holding_address_,
            asset_id_=collateral_id_,
            amount_=leveraged_amount_out,
        );

        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // If the position is leveraged, deposit the borrowed funds to Liquidity Fund
    if (current_position.leverage != LEVERAGE_ONE) {
        ILiquidityFund.deposit(
            contract_address=liquidity_fund_address_,
            asset_id_=collateral_id_,
            amount=borrowed_amount_to_be_returned,
            position_id_=order_.order_id,
        );

        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    tempvar syscall_ptr = syscall_ptr;
    tempvar range_check_ptr = range_check_ptr;

    // Check if the account value for the position is negative
    let (is_underwater) = Math64x61_is_le(margin_plus_pnl, 0, collateral_token_decimal_);

    // User's position has lost some amount of borrowed funds
    if (is_underwater == TRUE) {
        // Absolute value of the margin_plus_pnl
        let amount_to_transfer_from = abs_value(margin_plus_pnl);

        // Get the balance of user that is not locked
        let (user_unused_balance) = IAccountManager.get_unused_balance(
            contract_address=order_.user_address, assetID_=collateral_id_
        );

        // Check if the user's balance can cover the deficit
        let (is_balance_sufficient) = Math64x61_is_le(
            amount_to_transfer_from, user_unused_balance, collateral_token_decimal_
        );

        if (is_balance_sufficient == FALSE) {
            let (is_balance_less_than_zero) = Math64x61_is_le(
                user_unused_balance, 0, collateral_token_decimal_
            );
            if (is_balance_less_than_zero == TRUE) {
                IInsuranceFund.withdraw(
                    contract_address=insurance_fund_address_,
                    asset_id_=collateral_id_,
                    amount=amount_to_transfer_from,
                    position_id_=order_.order_id,
                );
                tempvar syscall_ptr = syscall_ptr;
                tempvar range_check_ptr = range_check_ptr;
            } else {
                let (deduct_from_insurance) = Math64x61_sub(
                    amount_to_transfer_from, user_unused_balance
                );
                IInsuranceFund.withdraw(
                    contract_address=insurance_fund_address_,
                    asset_id_=collateral_id_,
                    amount=deduct_from_insurance,
                    position_id_=order_.order_id,
                );
                tempvar syscall_ptr = syscall_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }

        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;

        // User's position value has become negative, it's a deficit for Holding contract as well
        if (is_le(0, leveraged_amount_out) == FALSE) {
            let holding_deficit = abs_value(leveraged_amount_out);

            IHolding.deposit(
                contract_address=holding_address_, asset_id_=collateral_id_, amount_=holding_deficit
            );

            tempvar syscall_ptr = syscall_ptr;
            tempvar range_check_ptr = range_check_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        } else {
            tempvar syscall_ptr = syscall_ptr;
            tempvar range_check_ptr = range_check_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        }

        // locked_margin needs to be taken from the user account
        let (total_amount_to_transfer_from) = Math64x61_add(
            amount_to_transfer_from, margin_amount_to_be_reduced
        );

        // Get locked_margin + margin_plus_pnl from the user account
        IAccountManager.transfer_from(
            contract_address=order_.user_address,
            asset_id_=collateral_id_,
            market_id_=market_id_,
            amount_=total_amount_to_transfer_from,
            invoked_for_='holding',
        );

        let (signed_realized_pnl) = Math64x61_mul(total_amount_to_transfer_from, NEGATIVE_ONE);
        realized_pnl = signed_realized_pnl;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        // If it's not a liquidation order
        if (is_le(order_.order_type, 3) == TRUE) {
            if (is_le(pnl, 0) == TRUE) {
                IAccountManager.transfer_from(
                    contract_address=order_.user_address,
                    asset_id_=collateral_id_,
                    market_id_=market_id_,
                    amount_=abs_value(pnl),
                    invoked_for_='holding',
                );
            } else {
                IAccountManager.transfer(
                    contract_address=order_.user_address,
                    asset_id_=collateral_id_,
                    market_id_=market_id_,
                    amount_=pnl,
                    invoked_for_='holding',
                );
            }

            realized_pnl = pnl;
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            if (order_.order_type == LIQUIDATION_ORDER) {
                // Deposit the user's remaining margin in Insurance Fund
                IInsuranceFund.deposit(
                    contract_address=insurance_fund_address_,
                    asset_id_=collateral_id_,
                    amount=margin_plus_pnl,
                    position_id_=order_.order_id,
                );

                IAccountManager.transfer_from(
                    contract_address=order_.user_address,
                    asset_id_=collateral_id_,
                    market_id_=market_id_,
                    amount_=margin_amount_to_be_reduced,
                    invoked_for_='holding',
                );

                let (signed_realized_pnl) = Math64x61_mul(
                    margin_amount_to_be_reduced, NEGATIVE_ONE
                );
                realized_pnl = signed_realized_pnl;
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            } else {
                realized_pnl = 0;
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    return (
        average_execution_price_close,
        margin_amount_close,
        borrowed_amount_close,
        realized_pnl,
        margin_amount_to_be_reduced,
    );
}

// @notice Internal function called by execute_batch
// @param batch_id_ - ID of the batch
// @param market_id_ - Market ID of the batch
// @param collateralID_ - Collateral ID of the batch to be set by the first order
// @param asset_token_decimal_ - No.of token decimals of an asset
// @param collateral_token_decimal_ - No.of token decimals of collateral
// @param orders_len_ - Length fo the execute batch (to be used to calculate the index of each order)
// @param request_list_len_ - No of orders in the batch
// @param request_list_ - The batch of the orders
// @param quantity_executed_ - Quantity of maker orders executed so far
// @param account_registry_address_ - Address of the Account Registry contract
// @param holding_address_ - Address of the Holding contract
// @param trading_fees_address_ - Address of the Trading contract
// @param fees_balance_address_ - Address of the Fee Balance contract
// @param liquidate_address_ - Address of the Liquidate contract
// @param liquidity_fund_address_ - Address of the Liquidity Fund contract
// @param insurance_fund_address_ - Address of the Insurance Fund contract
// @param max_leverage_ - Maximum Leverage for the market set by the first order
// @param min_quantity_ - Minimum quantity for the market set by the first order
// @param maker1_direction_ - Direction of the first maker order
// @param maker1_side_ - Side of the first maker order
// @param trader_stats_list_ - This list contains trader addresses along with fee charged
// @param total_order_volume_ - This stores the sum of size*execution_price for each maker order
// @param taker_execution_price - The price to be stored for the market price in execute_batch
// @param open_interest_ - Open interest corresponding to the current order
// @param oracle_price_ - Oracle price from the ZKXNode network
// @param execution_sizes_ - Execution sizes array
// @return res - returns the net sum of the orders do far
// @return trader_stats_list_len - length of the trader fee list so far
// @return open_interest - open interest corresponding to the trade batch
func check_and_execute{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    batch_id_: felt,
    market_id_: felt,
    collateral_id_: felt,
    asset_token_decimal_: felt,
    collateral_token_decimal_: felt,
    orders_len_: felt,
    request_list_len_: felt,
    request_list_: MultipleOrder*,
    quantity_executed_: felt,
    account_registry_address_: felt,
    holding_address_: felt,
    trading_fees_address_: felt,
    fees_balance_address_: felt,
    liquidate_address_: felt,
    liquidity_fund_address_: felt,
    insurance_fund_address_: felt,
    max_leverage_: felt,
    min_quantity_: felt,
    maker1_direction_: felt,
    maker1_side_: felt,
    trader_stats_list_: TraderStats*,
    total_order_volume_: felt,
    taker_execution_price: felt,
    open_interest_: felt,
    oracle_price_: felt,
    execution_sizes_: felt*,
) -> (taker_execution_price: felt, open_interest: felt) {
    alloc_locals;

    local execution_price;
    local margin_amount;
    local borrowed_amount;
    local margin_lock_update_amount;
    local average_execution_price;
    local new_total_order_volume;
    local quantity_to_execute;
    local current_quantity_executed;
    local current_order_side;
    local current_open_interest;
    local opening_fee;
    local pnl;

    // Local variables to be passed as arguments in error_messages
    local order_id;
    local leverage;
    local market_id_order;
    local quantity_order;
    local user_address;

    // Error messages require local variables to be passed in params
    local current_index;
    assert current_index = orders_len_ - request_list_len_;

    // Check if the list is empty, if yes return 1
    if (request_list_len_ == 0) {
        let (actual_open_interest) = Math64x61_div(open_interest_, TWO);
        return (taker_execution_price, actual_open_interest);
    }

    assert order_id = [request_list_].order_id;
    assert leverage = [request_list_].leverage;
    assert market_id_order = [request_list_].market_id;
    assert quantity_order = [request_list_].quantity;
    assert user_address = [request_list_].user_address;

    // check that the user account is present in account registry (and thus that it was deployed by zkx)
    let (is_registered) = IAccountRegistry.is_registered_user(
        contract_address=account_registry_address_, address_=user_address
    );

    with_attr error_message("0510: {order_id} {user_address}") {
        assert_not_zero(is_registered);
    }

    // Size Check
    with_attr error_message("0505: {order_id} {quantity_order}") {
        Math64x61_assert_le(min_quantity_, [request_list_].quantity, asset_token_decimal_);
    }

    // Market Check
    with_attr error_message("0504: {order_id} {market_id_order}") {
        assert [request_list_].market_id = market_id_;
    }

    // Leverage check minimum
    with_attr error_message("0503: {order_id} {leverage}") {
        assert_le(LEVERAGE_ONE, [request_list_].leverage);
    }

    // Leverage check maximum
    with_attr error_message("0502: {order_id} {leverage}") {
        assert_le([request_list_].leverage, max_leverage_);
    }

    // Taker Order
    if (request_list_len_ == 1) {
        // Direction Check
        validate_taker(
            order_id,
            maker1_direction_,
            maker1_side_,
            [request_list_].direction,
            [request_list_].side,
        );

        // Check for post-only flag; they must always be a maker
        with_attr error_message("0515: {order_id} {current_index}") {
            assert [request_list_].post_only = FALSE;
        }

        local taker_quantity;
        assert taker_quantity = [execution_sizes_];
        // Check for F&K type of orders; they must only be filled completely or rejected
        if ([request_list_].time_in_force == FoK) {
            let (diff_check) = Math64x61_sub([request_list_].quantity, taker_quantity);

            with_attr error_message("0516: {order_id} {taker_quantity}") {
                let (is_zero) = Math64x61_is_equal(diff_check, 0, asset_token_decimal_);
                assert is_zero = TRUE;
                assert [request_list_].order_type = LIMIT_ORDER;
            }

            tempvar syscall_ptr = syscall_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            tempvar syscall_ptr = syscall_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }

        // The execution price of a taker order is the weighted mean of the Maker orders
        let (new_execution_price: felt) = Math64x61_div(total_order_volume_, taker_quantity);
        assert execution_price = new_execution_price;

        // Price check
        if ([request_list_].order_type == LIMIT_ORDER) {
            check_limit_price(
                order_id_=order_id,
                price_=[request_list_].price,
                execution_price_=new_execution_price,
                direction_=[request_list_].direction,
                side_=[request_list_].side,
                collateral_token_decimal_=collateral_token_decimal_,
            );
        } else {
            check_within_slippage(
                order_id_=order_id,
                slippage_=[request_list_].slippage,
                oracle_price_=oracle_price_,
                execution_price_=execution_price,
                direction_=[request_list_].direction,
                side_=[request_list_].side,
                collateral_token_decimal_=collateral_token_decimal_,
            );
        }

        // Reset the variable
        assert current_quantity_executed = 0;

        // Reset the variable
        assert new_total_order_volume = 0;

        // Set the current side as taker
        assert current_order_side = TAKER;

        // Set quantity to execute
        assert quantity_to_execute = taker_quantity;

        // Emit the event
        let (keys: felt*) = alloc();
        assert keys[0] = 'trade_execution';
        assert keys[1] = market_id_;
        assert keys[2] = batch_id_;
        let (data: felt*) = alloc();
        assert data[0] = quantity_to_execute;
        assert data[1] = execution_price;
        assert data[2] = [request_list_].direction;
        assert data[3] = [request_list_].side;

        emit_event(2, keys, 4, data);

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        // Maker Order
        // Check the direction of the maker
        validate_maker(
            order_id,
            maker1_direction_,
            maker1_side_,
            [request_list_].direction,
            [request_list_].side,
        );

        with_attr error_message("0518: {order_id} {current_index}") {
            assert [request_list_].order_type = LIMIT_ORDER;
        }

        assert quantity_to_execute = [execution_sizes_];

        // Send to AccountManager to emit an event in case the execution_price is 0
        if (quantity_to_execute == 0) {
            // Create a temporary order object
            let temp_order_request: OrderRequest = OrderRequest(
                order_id=[request_list_].order_id,
                market_id=[request_list_].market_id,
                direction=[request_list_].direction,
                price=[request_list_].price,
                quantity=[request_list_].quantity,
                leverage=[request_list_].leverage,
                slippage=[request_list_].slippage,
                order_type=[request_list_].order_type,
                time_in_force=[request_list_].time_in_force,
                post_only=[request_list_].post_only,
                side=[request_list_].side,
                liquidator_address=[request_list_].liquidator_address,
            );

            // Create a temporary signature object
            let temp_signature: Signature = Signature(
                r_value=[request_list_].sig_r, s_value=[request_list_].sig_s
            );

            // Call the account contract to initialize the order
            IAccountManager.execute_order(
                contract_address=user_address,
                batch_id=batch_id_,
                request=temp_order_request,
                signature=temp_signature,
                size=0,
                average_execution_price=0,
                execution_price=[request_list_].price,
                margin_amount=0,
                borrowed_amount=0,
                market_id=market_id_,
                collateral_id_=collateral_id_,
                pnl=0,
                opening_fee=0,
                side=MAKER,
                margin_lock_update_amount=0,
            );

            let element: TraderStats = TraderStats(
                trader_address=user_address,
                fee_64x61=0,
                order_volume_64x61=0,
                side=MAKER,
                pnl_64x61=0,
                margin_amount_64x61=0,
            );

            assert [trader_stats_list_] = element;

            return check_and_execute(
                batch_id_=batch_id_,
                market_id_=market_id_,
                collateral_id_=collateral_id_,
                asset_token_decimal_=asset_token_decimal_,
                collateral_token_decimal_=collateral_token_decimal_,
                orders_len_=orders_len_,
                request_list_len_=request_list_len_ - 1,
                request_list_=request_list_ + MultipleOrder.SIZE,
                quantity_executed_=quantity_executed_,
                account_registry_address_=account_registry_address_,
                holding_address_=holding_address_,
                trading_fees_address_=trading_fees_address_,
                fees_balance_address_=fees_balance_address_,
                liquidate_address_=liquidate_address_,
                liquidity_fund_address_=liquidity_fund_address_,
                insurance_fund_address_=insurance_fund_address_,
                max_leverage_=max_leverage_,
                min_quantity_=min_quantity_,
                maker1_direction_=maker1_direction_,
                maker1_side_=maker1_side_,
                trader_stats_list_=trader_stats_list_ + TraderStats.SIZE,
                total_order_volume_=total_order_volume_,
                taker_execution_price=0,
                open_interest_=open_interest_,
                oracle_price_=oracle_price_,
                execution_sizes_=execution_sizes_ + 1,
            );
        }

        // Add the executed quantity to the running sum of quantity executed
        let (current_quantity_executed_felt: felt) = Math64x61_add(
            quantity_executed_, [execution_sizes_]
        );
        // Write to local variable
        assert current_quantity_executed = current_quantity_executed_felt;

        // Limit price of the maker is used as the execution price
        assert execution_price = [request_list_].price;

        // Add to the weighted sum of the execution prices
        let (new_order_volume) = Math64x61_mul([request_list_].price, [execution_sizes_]);
        let (new_total_order_volume_) = Math64x61_add(new_order_volume, total_order_volume_);
        // Write to local variable
        assert new_total_order_volume = new_total_order_volume_;

        // Set the current side as maker
        assert current_order_side = MAKER;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // If the order is to be opened
    if ([request_list_].side == BUY) {
        let (
            average_execution_price_temp: felt,
            margin_amount_temp: felt,
            borrowed_amount_temp: felt,
            trading_fee: felt,
            margin_lock_amount: felt,
        ) = process_open_orders(
            order_=[request_list_],
            execution_price_=execution_price,
            order_size_=quantity_to_execute,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            collateral_token_decimal_=collateral_token_decimal_,
            liquidity_fund_address_=liquidity_fund_address_,
            liquidate_address_=liquidate_address_,
            holding_address_=holding_address_,
            trading_fees_address_=trading_fees_address_,
            fees_balance_address_=fees_balance_address_,
            trader_stats_list_=trader_stats_list_,
            side_=current_order_side,
        );
        assert margin_amount = margin_amount_temp;
        assert borrowed_amount = borrowed_amount_temp;
        assert average_execution_price = average_execution_price_temp;
        assert pnl = trading_fee;
        assert opening_fee = trading_fee;
        assert current_open_interest = quantity_to_execute;
        assert margin_lock_update_amount = margin_lock_amount;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        let (
            average_execution_price_temp: felt,
            margin_amount_temp: felt,
            borrowed_amount_temp: felt,
            realized_pnl: felt,
            margin_unlock_amount: felt,
        ) = process_close_orders(
            order_=[request_list_],
            execution_price_=execution_price,
            order_size_=quantity_to_execute,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            collateral_token_decimal_=collateral_token_decimal_,
            liquidity_fund_address_=liquidity_fund_address_,
            insurance_fund_address_=insurance_fund_address_,
            holding_address_=holding_address_,
            trader_stats_list_=trader_stats_list_,
        );
        assert margin_amount = margin_amount_temp;
        assert borrowed_amount = borrowed_amount_temp;
        assert average_execution_price = average_execution_price_temp;
        assert pnl = realized_pnl;
        assert opening_fee = 0;
        assert current_open_interest = 0 - quantity_to_execute;
        assert margin_lock_update_amount = margin_unlock_amount;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Create a temporary order object
    let temp_order_request: OrderRequest = OrderRequest(
        order_id=[request_list_].order_id,
        market_id=[request_list_].market_id,
        direction=[request_list_].direction,
        price=[request_list_].price,
        quantity=[request_list_].quantity,
        leverage=[request_list_].leverage,
        slippage=[request_list_].slippage,
        order_type=[request_list_].order_type,
        time_in_force=[request_list_].time_in_force,
        post_only=[request_list_].post_only,
        side=[request_list_].side,
        liquidator_address=[request_list_].liquidator_address,
    );

    // Create a temporary signature object
    let temp_signature: Signature = Signature(
        r_value=[request_list_].sig_r, s_value=[request_list_].sig_s
    );

    // Call the account contract to initialize the order
    IAccountManager.execute_order(
        contract_address=user_address,
        batch_id=batch_id_,
        request=temp_order_request,
        signature=temp_signature,
        size=quantity_to_execute,
        average_execution_price=average_execution_price,
        execution_price=execution_price,
        margin_amount=margin_amount,
        borrowed_amount=borrowed_amount,
        market_id=market_id_,
        collateral_id_=collateral_id_,
        pnl=pnl,
        opening_fee=opening_fee,
        side=current_order_side,
        margin_lock_update_amount=margin_lock_update_amount,
    );

    let (new_open_interest) = Math64x61_add(open_interest_, current_open_interest);

    return check_and_execute(
        batch_id_=batch_id_,
        market_id_=market_id_,
        collateral_id_=collateral_id_,
        asset_token_decimal_=asset_token_decimal_,
        collateral_token_decimal_=collateral_token_decimal_,
        orders_len_=orders_len_,
        request_list_len_=request_list_len_ - 1,
        request_list_=request_list_ + MultipleOrder.SIZE,
        quantity_executed_=current_quantity_executed,
        account_registry_address_=account_registry_address_,
        holding_address_=holding_address_,
        trading_fees_address_=trading_fees_address_,
        fees_balance_address_=fees_balance_address_,
        liquidate_address_=liquidate_address_,
        liquidity_fund_address_=liquidity_fund_address_,
        insurance_fund_address_=insurance_fund_address_,
        max_leverage_=max_leverage_,
        min_quantity_=min_quantity_,
        maker1_direction_=maker1_direction_,
        maker1_side_=maker1_side_,
        trader_stats_list_=trader_stats_list_ + TraderStats.SIZE,
        total_order_volume_=new_total_order_volume,
        taker_execution_price=execution_price,
        open_interest_=new_open_interest,
        oracle_price_=oracle_price_,
        execution_sizes_=execution_sizes_ + 1,
    );
}

// @notice Internal function to validate maker orders
// @param order_id_ - Id of the maker order
// @param maker1_direction_ - Direction of first maker order
// @param maker1_side_ - Side of first maker order
// @param current_direction_ - Direction of current maker order
// @param current_side_ -  Side of current maker order
func validate_maker{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_id_: felt,
    maker1_direction_: felt,
    maker1_side_: felt,
    current_direction_: felt,
    current_side_: felt,
) {
    alloc_locals;
    let (local opposite_direction) = get_opposite(maker1_direction_);
    let (local opposite_side) = get_opposite(maker1_side_);
    if (current_direction_ == maker1_direction_) {
        if (current_side_ == maker1_side_) {
            return ();
        }
    }

    if (current_direction_ == opposite_direction) {
        if (current_side_ == opposite_side) {
            return ();
        }
    }

    with_attr error_message("0512: {order_id_} {current_direction_}") {
        assert 0 = 1;
    }
    return ();
}

// @notice Internal function to validate taker orders
// @param order_id_ - Id of the taker order
// @param maker1_direction_ - Direction of first maker order
// @param maker1_side_ - Side of first maker order
// @param current_direction_ - Direction of current maker order
// @param current_side_ -  Side of current maker order
func validate_taker{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_id_: felt,
    maker1_direction_: felt,
    maker1_side_: felt,
    current_direction_: felt,
    current_side_: felt,
) {
    alloc_locals;
    let (local opposite_direction) = get_opposite(maker1_direction_);
    let (local opposite_side) = get_opposite(maker1_side_);
    if (current_direction_ == maker1_direction_) {
        if (current_side_ == opposite_side) {
            return ();
        }
    }

    if (current_direction_ == opposite_direction) {
        if (current_side_ == maker1_side_) {
            return ();
        }
    }

    with_attr error_message("0511: {order_id_} {current_direction_}") {
        assert 0 = 1;
    }
    return ();
}

// @notice Internal function to get oppsite side or direction of the order
// @param side_or_direction_ - Argument represents either side or direction
// @return res - Returns either opposite side or opposite direction of the order
func get_opposite{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    side_or_direction_: felt
) -> (res: felt) {
    if (side_or_direction_ == OPEN) {
        return (res=CLOSE);
    } else {
        return (res=OPEN);
    }
}
