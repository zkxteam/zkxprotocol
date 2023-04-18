%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.hash_state import hash_finalize, hash_init, hash_update
from starkware.cairo.common.math import abs_value, assert_lt, assert_le, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.starknet.common.syscalls import emit_event, get_block_timestamp

from contracts.Constants import (
    AccountRegistry_INDEX,
    Asset_INDEX,
    BUY,
    CLOSE,
    DELEVERAGING_ORDER,
    EXECUTED,
    FeeBalance_INDEX,
    FoK,
    Holding_INDEX,
    InsuranceFund_INDEX,
    IoC,
    LIMIT_ORDER,
    Liquidate_INDEX,
    LIQUIDATION_ORDER,
    LiquidityFund_INDEX,
    LONG,
    MAKER,
    Market_INDEX,
    MarketPrices_INDEX,
    OPEN,
    SELL,
    TAKER,
    TradingFees_INDEX,
    TradingStats_INDEX,
)
from contracts.DataTypes import (
    Asset,
    ExecutionDetails,
    LiquidatablePosition,
    Market,
    MultipleOrder,
    PositionDetails,
    Signature,
    TraderStats,
)

from contracts.interfaces.IAccountLiquidator import IAccountLiquidator
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
    Math64x61_div,
    Math64x61_is_equal,
    Math64x61_is_le,
    Math64x61_min,
    Math64x61_mul,
    Math64x61_ONE,
    Math64x61_sub,
    Math64x61_round,
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

// Stores the order_id to hash mapping
@storage_var
func order_id_mapping(order_id: felt) -> (hash: felt) {
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
// @param batch_id_ - Id of the batch
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

    let (status: felt) = batch_id_status.read(batch_id=batch_id_);
    with_attr error_message("0525: {batch_id_}") {
        assert status = FALSE;
    }

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

    // Get the market details
    let (market: Market) = IMarkets.get_market(
        contract_address=market_address, market_id_=market_id_
    );

    with_attr error_message("509: {market_id_} 0") {
        assert_not_zero(market.is_tradable);
    }

    with_attr error_message("522: {market_id_} 0") {
        assert_not_zero(quantity_locked_);
    }

    // Get the index of the Taker order
    let last_index = request_list_len - 1;

    let (initial_taker_locked: felt, error_code: felt) = find_initial_taker_locked(
        asset_token_decimal_=asset.token_decimal,
        market_id_=market_id_,
        request_=request_list[last_index],
        quantity_locked_=quantity_locked_,
        collateral_id_=collateral_id,
    );

    local order_id;
    local error_code_temp;
    assert order_id = request_list[last_index].order_id;
    assert error_code_temp = error_code;

    with_attr error_message("{error_code_temp}: {order_id} 0") {
        assert error_code = 0;
    }

    // Recursively loop through the orders in the batch
    let (taker_execution_price: felt, open_interest: felt) = process_and_execute_orders_recurse(
        batch_id_=batch_id_,
        taker_locked_quantity_=initial_taker_locked,
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
        total_order_volume_=0,
        taker_execution_price_=0,
        open_interest_=0,
        oracle_price_=oracle_price_,
        error_order_id_=0,
        error_code_=0,
        error_param_=0,
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

    // Initialize empty trader_stats_list
    let (trader_stats_list: TraderStats*) = alloc();

    // Initialize empty executed_sizes_list
    let (executed_sizes_list: felt*) = alloc();

    // Record TradingStats
    ITradingStats.record_trade_batch_stats(
        contract_address=trading_stats_address,
        market_id_=market_id_,
        execution_price_64x61_=taker_execution_price,
        request_list_len=request_list_len,
        request_list=request_list,
        trader_stats_list_len=0,
        trader_stats_list=trader_stats_list,
        executed_sizes_list_len=0,
        executed_sizes_list=executed_sizes_list,
        open_interest_=open_interest,
    );

    // Change the status of the batch to TRUE
    batch_id_status.write(batch_id=batch_id_, value=EXECUTED);

    return ();
}

// ///////////
// Internal //
// ///////////

// @notice Internal function to calculate the amount that must be executed for an order
// @param order_portion_executed_ - Portion of the order that has already been executed
// @param position_details_ - Position details of the corresponding position
// @param asset_token_decimal_ - Number of decimals for the asset
// @param request_ - An order request
// @param quantity_remainging - Max quantity that can be executed for that order
// @returns quantity_to_execute_final - Calculated quantity to execute
// @returns error_code - Returns an error code if the adjsuted size is 0
func get_quantity_to_execute{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_portion_executed_: felt,
    market_id_: felt,
    position_details_: PositionDetails,
    asset_token_decimal_: felt,
    request_: MultipleOrder,
    liquidatable_position_: LiquidatablePosition,
    quantity_remaining_: felt,
) -> (quantity_to_execute_final: felt, error_code: felt) {
    alloc_locals;
    local quantity_to_execute;
    local quantity_to_execute_final;

    // Get min of remaining quantity and the order quantity
    let (executable_quantity: felt) = Math64x61_sub(request_.quantity, order_portion_executed_);
    let (quantity_to_execute) = Math64x61_min(executable_quantity, quantity_remaining_);

    // Return if the order is fully executed with the error code
    let (is_zero_quantity_to_execute) = Math64x61_is_equal(
        quantity_to_execute, 0, asset_token_decimal_
    );

    if (is_zero_quantity_to_execute == 1) {
        return (quantity_to_execute_final=0, error_code=523);
    }

    // If it's a sell order, calculate the amount that can be executed
    if (request_.side == SELL) {
        if (is_le(LIQUIDATION_ORDER, request_.order_type) == 1) {
            local error_code;

            // Error Handling: Wrong market for liquidation
            if (liquidatable_position_.market_id != market_id_) {
                return (quantity_to_execute_final=0, error_code=528);
            }

            // Error Handling: Wrong direction for liquidation
            if (liquidatable_position_.direction != request_.direction) {
                return (quantity_to_execute_final=0, error_code=529);
            }

            let (quantity_to_execute_liq) = Math64x61_min(
                quantity_to_execute, liquidatable_position_.amount_to_be_sold
            );

            // Return if the order is fully closed
            let (is_zero_quantity_to_execute) = Math64x61_is_equal(
                quantity_to_execute_liq, 0, asset_token_decimal_
            );

            if (is_zero_quantity_to_execute == TRUE) {
                assert error_code = 531;
            } else {
                assert error_code = 0;
            }

            return (quantity_to_execute_final=quantity_to_execute_liq, error_code=error_code);
        } else {
            local error_code;

            let (quantity_to_execute_non_liq) = Math64x61_min(
                quantity_to_execute, position_details_.position_size
            );

            // Return if the order is fully closed
            let (is_zero_quantity_to_execute) = Math64x61_is_equal(
                quantity_to_execute_non_liq, 0, asset_token_decimal_
            );

            if (is_zero_quantity_to_execute == TRUE) {
                assert error_code = 524;
            } else {
                assert error_code = 0;
            }

            return (quantity_to_execute_final=quantity_to_execute_non_liq, error_code=error_code);
        }
    } else {
        return (quantity_to_execute_final=quantity_to_execute, error_code=0);
    }
}

// @notice Internal function to adjust and calculate the quantity locked for the Taker order
// @param asset_token_decimal_ - Number of decimals for the asset
// @param request_ - Taker order details
// @param quantity_locked_ - Original quantity lokcked of the batch
// @returns taker_quantity_to_execute - Adjusted quantity to execute for the taker
// @returns error_code - Returns an error code if the adjsuted size is 0
func find_initial_taker_locked{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_token_decimal_: felt,
    market_id_: felt,
    request_: MultipleOrder,
    quantity_locked_: felt,
    collateral_id_: felt,
) -> (taker_quantity_to_execute: felt, error_code: felt) {
    // Get the portion executed of the order
    let (order_portion_executed: felt) = IAccountManager.get_portion_executed(
        contract_address=request_.user_address, order_id_=request_.order_id
    );

    // Get position details
    let (position_details: PositionDetails) = IAccountManager.get_position_data(
        contract_address=request_.user_address,
        market_id_=request_.market_id,
        direction_=request_.direction,
    );

    // Get liquidatable position details
    let (
        liq_position: LiquidatablePosition
    ) = IAccountManager.get_deleveragable_or_liquidatable_position(
        contract_address=request_.user_address, collateral_id_=collateral_id_
    );

    // Adjust the quantity to execute on the taker side
    let (taker_quantity_to_execute: felt, error_code: felt) = get_quantity_to_execute(
        order_portion_executed_=order_portion_executed,
        market_id_=market_id_,
        position_details_=position_details,
        asset_token_decimal_=asset_token_decimal_,
        request_=request_,
        liquidatable_position_=liq_position,
        quantity_remaining_=quantity_locked_,
    );

    return (taker_quantity_to_execute, error_code);
}

// @notice Internal function to check to check the slippage of a market order
// @param slippage_ - Slippage % of the order
// @param oracle_price_ - Oracle price of the batch
// @param execution_price_ - Execution price of the order
// @param direction_ - Direction of the order
// @param side_ - Side of the order BUY/SELL
// @param collateral_token_decimal_ - Decimals of the collateral
// @returns is_error - True if there's an error; else False
func check_within_slippage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    slippage_: felt,
    oracle_price_: felt,
    execution_price_: felt,
    direction_: felt,
    side_: felt,
    collateral_token_decimal_: felt,
) -> (is_error: felt) {
    // To remove
    alloc_locals;

    let (percentage) = Math64x61_div(slippage_, HUNDRED);
    let (threshold) = Math64x61_mul(percentage, oracle_price_);

    let (lower_limit: felt) = Math64x61_sub(oracle_price_, threshold);
    let (upper_limit: felt) = Math64x61_add(oracle_price_, threshold);

    if (direction_ == side_) {
        let (slippage_check) = Math64x61_is_le(
            execution_price_, upper_limit, collateral_token_decimal_
        );
        if (slippage_check == FALSE) {
            return (TRUE,);
        }
    } else {
        let (slippage_check) = Math64x61_is_le(
            lower_limit, execution_price_, collateral_token_decimal_
        );
        if (slippage_check == FALSE) {
            return (TRUE,);
        }
    }

    return (FALSE,);
}

// @notice Internal function to check if the execution_price of a limit order is valid (TAKER)
// @param price_ - Limit price of the order
// @param execution_price_ - Execution price of the order
// @param direction_ - Direction of the order
// @param side_ - Side of the order BUY/SELL
// @param collateral_token_decimal_ - Number of decimals for the collateral
// @returns is_error - True if there's an error; else False
// @returms error_message - Corresponding error message
func check_limit_price{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    price_: felt,
    execution_price_: felt,
    direction_: felt,
    side_: felt,
    collateral_token_decimal_: felt,
) -> (is_error: felt, error_message: felt) {
    alloc_locals;

    if (direction_ == LONG) {
        // if it's a long order
        if (side_ == BUY) {
            let (limit_price_check_1) = Math64x61_is_le(
                execution_price_, price_, collateral_token_decimal_
            );

            if (limit_price_check_1 == FALSE) {
                // if it's a buy order
                return (TRUE, 508);
            }
        } else {
            // if it's a sell order
            let (limit_price_check_2) = Math64x61_is_le(
                price_, execution_price_, collateral_token_decimal_
            );

            if (limit_price_check_2 == FALSE) {
                return (TRUE, 507);
            }
        }
        tempvar range_check_ptr = range_check_ptr;
    } else {
        // if it's a short order
        if (side_ == BUY) {
            // if it's a buy order
            let (limit_price_check_3) = Math64x61_is_le(
                price_, execution_price_, collateral_token_decimal_
            );

            if (limit_price_check_3 == FALSE) {
                return (TRUE, 507);
            }
        } else {
            // if it's a sell order
            let (limit_price_check_4) = Math64x61_is_le(
                execution_price_, price_, collateral_token_decimal_
            );

            if (limit_price_check_4 == FALSE) {
                return (TRUE, 508);
            }
        }
        tempvar range_check_ptr = range_check_ptr;
    }

    return (0, 0);
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
// @param trading_fees_address_ - Address of the Trading fees contract
// @param fees_balance_address_ - Address of the Fee Balance contract
// @param side_ - TAKER/MAKER
// @returns error_code - Returns an error code, if there's an error
// @returns user_available_balance - Available margin of the user
// @returns average_execution_price_open - Average Execution Price for the order
// @returns margin_amount_open - New Margin amount for the position
// @returns borrowed_amount_open - New Borrowed amount for the position
// @returns trading_fee - Trading fee for the order
// @returns margin_lock_amount - Margin to be locked in AccountManager
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
    side_: felt,
) -> (
    error_code: felt,
    user_available_balance: felt,
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
    let (available_margin, is_liquidation) = ILiquidate.check_for_risk(
        contract_address=liquidate_address_,
        order_=order_,
        size=order_size_,
        execution_price_=execution_price_,
        margin_amount_=margin_order_value,
    );

    // Setting local values to be used in error message
    assert user_available_balance = available_margin;
    assert order_id = order_.order_id;

    if (is_liquidation == TRUE) {
        return (531, user_available_balance, 0, 0, 0, 0, 0);
    }

    let (user_balance_check) = Math64x61_is_le(
        fees, user_available_balance, collateral_token_decimal_
    );

    if (user_balance_check == FALSE) {
        return (501, user_available_balance, 0, 0, 0, 0, 0);
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
        FALSE,
        user_available_balance,
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
// @returns margin_amount_close - New margin amount for the position
// @returns borrowed_amount_close - New borrowed amount for the position
// @returns average_execution_price_open - Average Execution Price for the position
// @returns realized_pnl - New realized pnl amount for the position
// @returns margin_unlock_amount - Margin amount to be unlocked in the AccountManager
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
        let (local user_balance) = IAccountManager.get_balance(
            contract_address=order_.user_address, assetID_=collateral_id_
        );
        // If it's not a liquidation order
        if (is_le(order_.order_type, 3) == TRUE) {
            // if the user is in loss
            if (is_le(pnl, 0) == TRUE) {
                let pnl_abs = abs_value(pnl);
                let (is_balance_sufficient) = Math64x61_is_le(
                    pnl_abs, user_balance, collateral_token_decimal_
                );
                // if user balance <= 0, deduct from insurance the whole loss amount
                if (is_balance_sufficient == FALSE) {
                    let (is_balance_less_than_zero) = Math64x61_is_le(
                        user_balance, 0, collateral_token_decimal_
                    );
                    if (is_balance_less_than_zero == TRUE) {
                        IInsuranceFund.withdraw(
                            contract_address=insurance_fund_address_,
                            asset_id_=collateral_id_,
                            amount=pnl_abs,
                            position_id_=order_.order_id,
                        );
                        tempvar syscall_ptr = syscall_ptr;
                        tempvar range_check_ptr = range_check_ptr;
                        // if user has some balance, deduct only remaining from insurance
                    } else {
                        let (deduct_from_insurance) = Math64x61_sub(pnl_abs, user_balance);
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
                    tempvar range_check_ptr = range_check_ptr;
                    // if user balance can cover whole loss, don't do anything
                } else {
                    tempvar syscall_ptr = syscall_ptr;
                    tempvar range_check_ptr = range_check_ptr;
                }
                IAccountManager.transfer_from(
                    contract_address=order_.user_address,
                    asset_id_=collateral_id_,
                    market_id_=market_id_,
                    amount_=pnl_abs,
                    invoked_for_='holding',
                );
                // if user is in profit
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
                let (is_balance_sufficient) = Math64x61_is_le(
                    margin_amount_to_be_reduced, user_balance, collateral_token_decimal_
                );
                // if user balance >= margin amount, deposit remaining margin in insurance
                if (is_balance_sufficient == TRUE) {
                    IInsuranceFund.deposit(
                        contract_address=insurance_fund_address_,
                        asset_id_=collateral_id_,
                        amount=margin_plus_pnl,
                        position_id_=order_.order_id,
                    );
                } else {
                    let (is_balance_less_than_zero) = Math64x61_is_le(
                        user_balance, 0, collateral_token_decimal_
                    );
                    // if user balance <= 0, deduct margin amount from insurance
                    if (is_balance_less_than_zero == TRUE) {
                        IInsuranceFund.withdraw(
                            contract_address=insurance_fund_address_,
                            asset_id_=collateral_id_,
                            amount=margin_amount_to_be_reduced,
                            position_id_=order_.order_id,
                        );
                        tempvar syscall_ptr = syscall_ptr;
                        tempvar range_check_ptr = range_check_ptr;
                        // if user has some balance
                    } else {
                        let pnl_abs = abs_value(pnl);
                        let (is_balance_less_than_loss) = Math64x61_is_le(
                            user_balance, pnl_abs, collateral_token_decimal_
                        );
                        // if user balance can't cover loss, deduct deficit from insurance
                        if (is_balance_less_than_loss == TRUE) {
                            let (deduct_from_insurance) = Math64x61_sub(pnl_abs, user_balance);
                            IInsuranceFund.withdraw(
                                contract_address=insurance_fund_address_,
                                asset_id_=collateral_id_,
                                amount=deduct_from_insurance,
                                position_id_=order_.order_id,
                            );
                            tempvar syscall_ptr = syscall_ptr;
                            tempvar range_check_ptr = range_check_ptr;
                            // if user balance can cover loss, deposit remaining to insurance
                        } else {
                            let (deposit_to_insurance) = Math64x61_sub(user_balance, pnl_abs);
                            IInsuranceFund.deposit(
                                contract_address=insurance_fund_address_,
                                asset_id_=collateral_id_,
                                amount=deposit_to_insurance,
                                position_id_=order_.order_id,
                            );
                        }
                    }
                }

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
// @param taker_locked_quantity_ - Adjusted taker quantity
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
// @param total_order_volume_ - This stores the sum of size*execution_price for each maker order
// @param taker_execution_price - The price to be stored for the market price in execute_batch
// @param open_interest_ - Open interest corresponding to the current order
// @param oracle_price_ - Oracle price from the ZKXNode network
// @param error_order_id_ - Order id of the first Maker order that has an error
// @param error_code_ - Error code of the first Maker order that has an error
// @param error_param_ - Parameter of the above error
// @return taker_execution_price - The price at which the taker order was executed
// @return open_interest - open interest corresponding to the trade batch
func process_and_execute_orders_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*
}(
    batch_id_: felt,
    taker_locked_quantity_: felt,
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
    total_order_volume_: felt,
    taker_execution_price_: felt,
    open_interest_: felt,
    oracle_price_: felt,
    error_order_id_: felt,
    error_code_: felt,
    error_param_: felt,
) -> (taker_execution_price: felt, open_interest: felt) {
    alloc_locals;

    local execution_price;
    local new_total_order_volume;
    local quantity_to_execute;
    local current_quantity_executed;
    local current_order_side;
    local current_open_interest;
    local updated_portion_executed;
    local opening_fee;
    local updated_position_details: PositionDetails;
    local execution_details: ExecutionDetails;
    local order_id;
    local pnl;

    local market_array_update;
    local updated_margin_locked;
    local updated_liquidatable_position: LiquidatablePosition;
    local is_liquidation;

    // Error messages require local variables to be passed in params
    local current_index;
    assert current_index = orders_len_ - request_list_len_;

    // Check if the list is empty, if yes return 1
    if (request_list_len_ == 0) {
        let (actual_open_interest) = Math64x61_div(open_interest_, TWO);

        return (taker_execution_price=taker_execution_price_, open_interest=actual_open_interest);
    }
    // Set order_id for AccountManager events
    assert order_id = [request_list_].order_id;

    // Error Handling: User is not registered
    // check that the user account is present in account registry (and thus that it was deployed by zkx)
    let (is_registered) = IAccountRegistry.is_registered_user(
        contract_address=account_registry_address_, address_=[request_list_].user_address
    );
    if (is_registered == FALSE) {
        local error_code;
        local error_order_id;
        local error_param;
        local user_address;

        assert user_address = [request_list_].user_address;

        if (request_list_len_ == 1) {
            if (error_order_id_ == 0) {
                with_attr error_message("510: {order_id} {user_address}") {
                    assert 1 = 0;
                }
            } else {
                with_attr error_message("{error_code_}: {error_order_id_} {error_param_}") {
                    assert 1 = 0;
                }
            }
        } else {
            if (error_order_id_ == 0) {
                assert error_code = 510;
                assert error_order_id = order_id;
                assert error_param = user_address;
            } else {
                assert error_code = error_code_;
                assert error_order_id = error_order_id_;
                assert error_param = error_param_;
            }
        }

        // Call the account contract to reject the order
        IAccountManager.execute_order(
            contract_address=[request_list_].user_address,
            batch_id_=batch_id_,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
            updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
            updated_margin_locked_=0,
            updated_portion_executed_=0,
            market_array_update_=0,
            is_liquidation_=0,
            error_message_=510,
            error_param_1_=[request_list_].user_address,
        );

        return process_and_execute_orders_recurse(
            batch_id_=batch_id_,
            taker_locked_quantity_=taker_locked_quantity_,
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
            total_order_volume_=total_order_volume_,
            taker_execution_price_=taker_execution_price_,
            open_interest_=open_interest_,
            oracle_price_=oracle_price_,
            error_order_id_=error_order_id,
            error_code_=error_code,
            error_param_=error_param,
        );
    }

    // Error Handling: Quantity is less than the one set for the market
    let (size_check) = Math64x61_is_le(
        min_quantity_, [request_list_].quantity, asset_token_decimal_
    );
    if (size_check == FALSE) {
        local error_code;
        local error_order_id;
        local error_param;
        local quantity;

        assert quantity = [request_list_].quantity;

        if (request_list_len_ == 1) {
            if (error_order_id_ == 0) {
                with_attr error_message("505: {order_id} {quantity}") {
                    assert 1 = 0;
                }
            } else {
                if (quantity_executed_ == 0) {
                    with_attr error_message("{error_code_}: {error_order_id_} {error_param_}") {
                        assert 1 = 0;
                    }
                } else {
                    with_attr error_message("505: {order_id} {quantity}") {
                        assert 1 = 0;
                    }
                }
            }
        } else {
            if (error_order_id_ == 0) {
                assert error_code = 505;
                assert error_order_id = order_id;
                assert error_param = quantity;
            } else {
                assert error_code = error_code_;
                assert error_order_id = error_order_id_;
                assert error_param = error_param_;
            }
        }

        // Call the account contract to reject the order
        IAccountManager.execute_order(
            contract_address=[request_list_].user_address,
            batch_id_=batch_id_,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
            updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
            updated_margin_locked_=0,
            updated_portion_executed_=0,
            market_array_update_=0,
            is_liquidation_=0,
            error_message_=505,
            error_param_1_=[request_list_].quantity,
        );

        return process_and_execute_orders_recurse(
            batch_id_=batch_id_,
            taker_locked_quantity_=taker_locked_quantity_,
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
            total_order_volume_=total_order_volume_,
            taker_execution_price_=taker_execution_price_,
            open_interest_=open_interest_,
            oracle_price_=oracle_price_,
            error_order_id_=error_order_id,
            error_code_=error_code,
            error_param_=error_param,
        );
    }

    // Error Handling: Wrong market passed for the order
    if ([request_list_].market_id != market_id_) {
        local error_code;
        local error_order_id;
        local error_param;
        local market_id_temp;

        assert market_id_temp = [request_list_].market_id;

        if (request_list_len_ == 1) {
            if (error_order_id_ == 0) {
                with_attr error_message("504: {order_id} {market_id_temp}") {
                    assert 1 = 0;
                }
            } else {
                if (quantity_executed_ == 0) {
                    with_attr error_message("{error_code_}: {error_order_id_} {error_param_}") {
                        assert 1 = 0;
                    }
                } else {
                    with_attr error_message("504: {order_id} {market_id_temp}") {
                        assert 1 = 0;
                    }
                }
            }
        } else {
            if (error_order_id_ == 0) {
                assert error_code = 504;
                assert error_order_id = order_id;
                assert error_param = market_id_temp;
            } else {
                assert error_code = error_code_;
                assert error_order_id = error_order_id_;
                assert error_param = error_param_;
            }
        }
        // Call the account contract to reject the order
        IAccountManager.execute_order(
            contract_address=[request_list_].user_address,
            batch_id_=batch_id_,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
            updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
            updated_margin_locked_=0,
            updated_portion_executed_=0,
            market_array_update_=0,
            is_liquidation_=0,
            error_message_=504,
            error_param_1_=[request_list_].market_id,
        );

        return process_and_execute_orders_recurse(
            batch_id_=batch_id_,
            taker_locked_quantity_=taker_locked_quantity_,
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
            total_order_volume_=total_order_volume_,
            taker_execution_price_=taker_execution_price_,
            open_interest_=open_interest_,
            oracle_price_=oracle_price_,
            error_order_id_=error_order_id,
            error_code_=error_code,
            error_param_=error_param,
        );
    }

    // Error Handling: Invalid leverage; leverage < minimum
    let (leverage_min_check) = Math64x61_is_le(
        LEVERAGE_ONE, [request_list_].leverage, asset_token_decimal_
    );
    if (leverage_min_check == FALSE) {
        local error_code;
        local error_order_id;
        local error_param;
        local leverage;

        assert leverage = [request_list_].leverage;

        if (request_list_len_ == 1) {
            if (error_order_id_ == 0) {
                with_attr error_message("503: {order_id} {leverage}") {
                    assert 1 = 0;
                }
            } else {
                if (quantity_executed_ == 0) {
                    with_attr error_message("{error_code_}: {error_order_id_} {error_param_}") {
                        assert 1 = 0;
                    }
                } else {
                    with_attr error_message("503: {order_id} {leverage}") {
                        assert 1 = 0;
                    }
                }
            }
        } else {
            if (error_order_id_ == 0) {
                assert error_code = 503;
                assert error_order_id = order_id;
                assert error_param = leverage;
            } else {
                assert error_code = error_code_;
                assert error_order_id = error_order_id_;
                assert error_param = error_param_;
            }
        }

        // Call the account contract to reject the order
        IAccountManager.execute_order(
            contract_address=[request_list_].user_address,
            batch_id_=batch_id_,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
            updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
            updated_margin_locked_=0,
            updated_portion_executed_=0,
            market_array_update_=0,
            is_liquidation_=0,
            error_message_=503,
            error_param_1_=[request_list_].leverage,
        );

        return process_and_execute_orders_recurse(
            batch_id_=batch_id_,
            taker_locked_quantity_=taker_locked_quantity_,
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
            total_order_volume_=total_order_volume_,
            taker_execution_price_=taker_execution_price_,
            open_interest_=open_interest_,
            oracle_price_=oracle_price_,
            error_order_id_=error_order_id,
            error_code_=error_code,
            error_param_=error_param,
        );
    }

    // Invalid leverage; leverage > maximum
    let (leverage_max_check) = Math64x61_is_le(
        [request_list_].leverage, max_leverage_, asset_token_decimal_
    );
    if (leverage_max_check == FALSE) {
        local error_code;
        local error_order_id;
        local error_param;
        local leverage;

        assert leverage = [request_list_].leverage;

        if (request_list_len_ == 1) {
            if (error_order_id_ == 0) {
                with_attr error_message("502: {order_id} {leverage}") {
                    assert 1 = 0;
                }
            } else {
                if (quantity_executed_ == 0) {
                    with_attr error_message("{error_code_}: {error_order_id_} {error_param_}") {
                        assert 1 = 0;
                    }
                } else {
                    with_attr error_message("502: {order_id} {leverage}") {
                        assert 1 = 0;
                    }
                }
            }
        } else {
            if (error_order_id_ == 0) {
                assert error_code = 502;
                assert error_order_id = order_id;
                assert error_param = leverage;
            } else {
                assert error_code = error_code_;
                assert error_order_id = error_order_id_;
                assert error_param = error_param_;
            }
        }
        // Call the account contract to reject the order
        IAccountManager.execute_order(
            contract_address=[request_list_].user_address,
            batch_id_=batch_id_,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
            updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
            updated_margin_locked_=0,
            updated_portion_executed_=0,
            market_array_update_=0,
            is_liquidation_=0,
            error_message_=502,
            error_param_1_=[request_list_].leverage,
        );

        return process_and_execute_orders_recurse(
            batch_id_=batch_id_,
            taker_locked_quantity_=taker_locked_quantity_,
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
            total_order_volume_=total_order_volume_,
            taker_execution_price_=taker_execution_price_,
            open_interest_=open_interest_,
            oracle_price_=oracle_price_,
            error_order_id_=error_order_id,
            error_code_=error_code,
            error_param_=error_param,
        );
    }

    // Get the portion executed of the order
    let (order_portion_executed: felt) = IAccountManager.get_portion_executed(
        contract_address=[request_list_].user_address, order_id_=[request_list_].order_id
    );

    // Get position details
    let (position_details: PositionDetails) = IAccountManager.get_position_data(
        contract_address=[request_list_].user_address,
        market_id_=[request_list_].market_id,
        direction_=[request_list_].direction,
    );

    // Get the locked margin details from the AccountManager
    let (current_margin_locked) = IAccountManager.get_locked_margin(
        contract_address=[request_list_].user_address, assetID_=collateral_id_
    );

    // Get user's public key to check the signature
    let (user_public_key, auth_reg_addr) = IAccountManager.get_public_key(
        contract_address=[request_list_].user_address
    );

    let (
        liq_position: LiquidatablePosition
    ) = IAccountManager.get_deleveragable_or_liquidatable_position(
        contract_address=[request_list_].user_address, collateral_id_=collateral_id_
    );

    // Create a temporary order object
    tempvar temp_order_request: felt* = new (
        [request_list_].order_id,
        [request_list_].market_id,
        [request_list_].direction,
        [request_list_].price,
        [request_list_].quantity,
        [request_list_].leverage,
        [request_list_].slippage,
        [request_list_].order_type,
        [request_list_].time_in_force,
        [request_list_].post_only,
        [request_list_].side,
        [request_list_].liquidator_address,
    );

    // Code brought in from AccountManager
    // hash the parameters
    let (hash) = hash_order(temp_order_request);

    // Check for hash collision
    let (hash_error) = order_hash_check(order_id_=[request_list_].order_id, order_hash_=hash);

    if (hash_error == TRUE) {
        local error_code;
        local error_order_id;
        local error_param;
        local order_hash;

        assert order_hash = hash;

        if (request_list_len_ == 1) {
            if (error_order_id_ == 0) {
                with_attr error_message("525: {order_id} {order_hash}") {
                    assert 1 = 0;
                }
            } else {
                if (quantity_executed_ == 0) {
                    with_attr error_message("{error_code_}: {error_order_id_} {error_param_}") {
                        assert 1 = 0;
                    }
                } else {
                    with_attr error_message("525: {order_id} {order_hash}") {
                        assert 1 = 0;
                    }
                }
            }
        } else {
            if (error_order_id_ == 0) {
                assert error_code = 525;
                assert error_order_id = order_id;
                assert error_param = order_hash;
            } else {
                assert error_code = error_code_;
                assert error_order_id = error_order_id_;
                assert error_param = error_param_;
            }
        }

        // Call the account contract to reject the order
        IAccountManager.execute_order(
            contract_address=[request_list_].user_address,
            batch_id_=batch_id_,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
            updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
            updated_margin_locked_=0,
            updated_portion_executed_=0,
            market_array_update_=0,
            is_liquidation_=0,
            error_message_=525,
            error_param_1_=hash,
        );

        return process_and_execute_orders_recurse(
            batch_id_=batch_id_,
            taker_locked_quantity_=taker_locked_quantity_,
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
            total_order_volume_=total_order_volume_,
            taker_execution_price_=taker_execution_price_,
            open_interest_=open_interest_,
            oracle_price_=oracle_price_,
            error_order_id_=error_order_id,
            error_code_=error_code,
            error_param_=error_param,
        );
    }

    // Create a signature object
    let user_signature: Signature = Signature(
        r_value=[request_list_].sig_r, s_value=[request_list_].sig_s
    );

    // check if signed by the user/liquidator
    is_valid_signature_order(
        hash=hash,
        signature=user_signature,
        liquidator_address_=[request_list_].liquidator_address,
        user_public_key_=user_public_key,
    );

    // Taker Order
    if (request_list_len_ == 1) {
        // Set the quantity to execute as the total quantity executed by the Maker so far
        assert quantity_to_execute = quantity_executed_;
        let (is_zero_quantity) = Math64x61_is_equal(quantity_executed_, 0, 6);

        with_attr error_message("{error_code_}: {error_order_id_} {error_param_}") {
            assert is_zero_quantity = FALSE;
        }

        // Direction Check
        let (is_error) = validate_taker(
            maker1_direction_, maker1_side_, [request_list_].direction, [request_list_].side
        );

        if (is_error == TRUE) {
            local direction;
            assert direction = [request_list_].direction;

            with_attr error_message("511: {order_id} {direction}") {
                assert 1 = 0;
            }
        }

        // Error Handling: A Taker order cannot be a post only order
        if ([request_list_].post_only == TRUE) {
            with_attr error_message("515: {order_id} {current_index}") {
                assert 1 = 0;
            }
        }

        local taker_quantity;
        assert taker_quantity = quantity_executed_;
        // Check for F&K type of orders; they must only be filled completely or rejected
        if ([request_list_].time_in_force == FoK) {
            let (diff_check) = Math64x61_sub([request_list_].quantity, taker_quantity);

            with_attr error_message("516: {order_id} {taker_quantity}") {
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
            let (is_error_1: felt, error_message_1: felt) = check_limit_price(
                price_=[request_list_].price,
                execution_price_=new_execution_price,
                direction_=[request_list_].direction,
                side_=[request_list_].side,
                collateral_token_decimal_=collateral_token_decimal_,
            );

            if (is_error_1 == TRUE) {
                local error_code_temp;

                assert error_code_temp = error_message_1;
                with_attr error_message("{error_code_temp}: {order_id} {execution_price}") {
                    assert 1 = 0;
                }
            }

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            local slippage;
            assert slippage = [request_list_].slippage;

            with_attr error_message("521: {order_id} {slippage}") {
                assert_lt(0, slippage);
                assert_le(slippage, FIFTEEN_PERCENTAGE);
            }

            let (is_error: felt) = check_within_slippage(
                slippage_=slippage,
                oracle_price_=oracle_price_,
                execution_price_=execution_price,
                direction_=[request_list_].direction,
                side_=[request_list_].side,
                collateral_token_decimal_=collateral_token_decimal_,
            );

            if (is_error == TRUE) {
                with_attr error_message("506: {order_id} {execution_price}") {
                    assert 1 = 0;
                }
            }
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
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

        emit_event(3, keys, 4, data);

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        // Maker Order

        // Find quantity left to be executed
        let (quantity_remaining) = Math64x61_sub(taker_locked_quantity_, quantity_executed_);

        // Find quantity that needs to be executed for the current order
        let (quantity_to_execute_remaining, error_code_quantity) = get_quantity_to_execute(
            order_portion_executed_=order_portion_executed,
            market_id_=market_id_,
            position_details_=position_details,
            asset_token_decimal_=asset_token_decimal_,
            request_=[request_list_],
            liquidatable_position_=liq_position,
            quantity_remaining_=quantity_remaining,
        );

        quantity_to_execute = quantity_to_execute_remaining;

        // Send to AccountManager to emit an event in case the execution size is 0
        if (error_code_quantity != 0) {
            local error_code;
            local error_order_id;
            local error_param;
            local error_code_temp;

            if (error_order_id_ == 0) {
                assert error_code = error_code_quantity;
                assert error_order_id = order_id;
                assert error_param = 0;
            } else {
                assert error_code = error_code_;
                assert error_order_id = error_order_id_;
                assert error_param = error_param_;
            }

            IAccountManager.execute_order(
                contract_address=[request_list_].user_address,
                batch_id_=batch_id_,
                market_id_=market_id_,
                collateral_id_=collateral_id_,
                execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
                updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
                updated_margin_locked_=0,
                updated_portion_executed_=0,
                market_array_update_=0,
                is_liquidation_=0,
                error_message_=error_code,
                error_param_1_=0,
            );

            return process_and_execute_orders_recurse(
                batch_id_=batch_id_,
                taker_locked_quantity_=taker_locked_quantity_,
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
                total_order_volume_=total_order_volume_,
                taker_execution_price_=taker_execution_price_,
                open_interest_=open_interest_,
                oracle_price_=oracle_price_,
                error_order_id_=error_order_id,
                error_code_=error_code,
                error_param_=error_param,
            );
        }

        // Check the direction of the maker
        let (is_error) = validate_maker(
            maker1_direction_, maker1_side_, [request_list_].direction, [request_list_].side
        );

        if (is_error == TRUE) {
            local error_code;
            local error_order_id;
            local error_param;
            local direction;

            assert direction = [request_list_].direction;

            if (request_list_len_ == 1) {
                with_attr error_message("512: {order_id} {direction}") {
                    assert 1 = 0;
                }
            } else {
                if (error_order_id_ == 0) {
                    assert error_code = 512;
                    assert error_order_id = order_id;
                    assert error_param = direction;
                } else {
                    assert error_code = error_code_;
                    assert error_order_id = error_order_id_;
                    assert error_param = error_param_;
                }
            }

            IAccountManager.execute_order(
                contract_address=[request_list_].user_address,
                batch_id_=batch_id_,
                market_id_=market_id_,
                collateral_id_=collateral_id_,
                execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
                updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
                updated_margin_locked_=0,
                updated_portion_executed_=0,
                market_array_update_=0,
                is_liquidation_=0,
                error_message_=512,
                error_param_1_=[request_list_].direction,
            );

            return process_and_execute_orders_recurse(
                batch_id_=batch_id_,
                taker_locked_quantity_=taker_locked_quantity_,
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
                total_order_volume_=total_order_volume_,
                taker_execution_price_=taker_execution_price_,
                open_interest_=open_interest_,
                oracle_price_=oracle_price_,
                error_order_id_=error_order_id,
                error_code_=error_code,
                error_param_=error_param,
            );
        }

        if ([request_list_].order_type != LIMIT_ORDER) {
            local error_code;
            local error_order_id;
            local error_param;

            if (request_list_len_ == 1) {
                with_attr error_message("518: {order_id} {current_index}") {
                    assert 1 = 0;
                }
            } else {
                if (error_order_id_ == 0) {
                    assert error_code = 518;
                    assert error_order_id = order_id;
                    assert error_param = current_index;
                } else {
                    assert error_code = error_code_;
                    assert error_order_id = error_order_id_;
                    assert error_param = error_param_;
                }
            }
            // Call the account contract to reject the order
            IAccountManager.execute_order(
                contract_address=[request_list_].user_address,
                batch_id_=batch_id_,
                market_id_=market_id_,
                collateral_id_=collateral_id_,
                execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
                updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
                updated_margin_locked_=0,
                updated_portion_executed_=0,
                market_array_update_=0,
                is_liquidation_=0,
                error_message_=518,
                error_param_1_=current_index,
            );

            return process_and_execute_orders_recurse(
                batch_id_=batch_id_,
                taker_locked_quantity_=taker_locked_quantity_,
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
                total_order_volume_=total_order_volume_,
                taker_execution_price_=taker_execution_price_,
                open_interest_=open_interest_,
                oracle_price_=oracle_price_,
                error_order_id_=error_order_id,
                error_code_=error_code,
                error_param_=error_param,
            );
        }

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        // Add the executed quantity to the running sum of quantity executed
        let (current_quantity_executed_felt: felt) = Math64x61_add(
            quantity_executed_, quantity_to_execute
        );
        // Write to local variable
        assert current_quantity_executed = current_quantity_executed_felt;

        // Limit price of the maker is used as the execution price
        assert execution_price = [request_list_].price;

        // Add to the weighted sum of the execution prices
        let (new_order_volume) = Math64x61_mul([request_list_].price, quantity_to_execute);
        let (new_total_order_volume_) = Math64x61_add(new_order_volume, total_order_volume_);
        // Write to local variable
        assert new_total_order_volume = new_total_order_volume_;

        // Set the current side as maker
        assert current_order_side = MAKER;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    let (local current_timestamp) = get_block_timestamp();

    // If the order is to be opened
    if ([request_list_].side == BUY) {
        let (
            error_code_open: felt,
            user_available_balance: felt,
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
            side_=current_order_side,
        );

        if (error_code_open != 0) {
            local error_code;
            local error_order_id;
            local error_param;
            local error_code_temp;

            assert error_code_temp = error_code_open;

            if (request_list_len_ == 1) {
                with_attr error_message("{error_code_temp}: {order_id} {market_id_}") {
                    assert 1 = 0;
                }
            } else {
                if (error_order_id_ == 0) {
                    assert error_code = error_code_temp;
                    assert error_order_id = order_id;
                    assert error_param = market_id_;
                } else {
                    assert error_code = error_code_;
                    assert error_order_id = error_order_id_;
                    assert error_param = error_param_;
                }
            }
            // Call the account contract to reject the order
            IAccountManager.execute_order(
                contract_address=[request_list_].user_address,
                batch_id_=batch_id_,
                market_id_=market_id_,
                collateral_id_=collateral_id_,
                execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
                updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
                updated_margin_locked_=0,
                updated_portion_executed_=0,
                market_array_update_=0,
                is_liquidation_=0,
                error_message_=error_code,
                error_param_1_=user_available_balance,
            );

            return process_and_execute_orders_recurse(
                batch_id_=batch_id_,
                taker_locked_quantity_=taker_locked_quantity_,
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
                total_order_volume_=total_order_volume_,
                taker_execution_price_=taker_execution_price_,
                open_interest_=open_interest_,
                oracle_price_=oracle_price_,
                error_order_id_=error_order_id,
                error_code_=error_code,
                error_param_=error_param,
            );
        }

        // Local variable to store the timestamp at which the position was opened
        local created_timestamp;

        // Round off the average execution price of the position
        let (local average_execution_price_rounded) = Math64x61_round(
            average_execution_price_temp, collateral_token_decimal_
        );

        // Check if the current position size is 0
        let (is_zero_current_position) = Math64x61_is_equal(
            position_details.position_size, 0, asset_token_decimal_
        );

        // If the current_position's size is 0
        if (is_zero_current_position == TRUE) {
            // Get the opposite position and check if the size of it is 0 as well
            let (opposite_direction: felt) = get_opposite(
                side_or_direction_=[request_list_].direction
            );
            let (opposite_position: PositionDetails) = IAccountManager.get_position_data(
                contract_address=[request_list_].user_address,
                market_id_=market_id_,
                direction_=opposite_direction,
            );
            let (is_zero_opposite_position) = Math64x61_is_equal(
                opposite_position.position_size, 0, asset_token_decimal_
            );

            // If the size is 0, we mark market_array_update needing add_to_market_array
            if (is_zero_opposite_position == TRUE) {
                assert market_array_update = 1;
            } else {
                assert market_array_update = 0;
            }

            created_timestamp = current_timestamp;

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            created_timestamp = position_details.created_timestamp;
            assert market_array_update = 0;

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        // Calculate the updated position data
        let (new_position_size) = Math64x61_add(
            position_details.position_size, quantity_to_execute
        );
        let (total_value) = Math64x61_add(margin_amount_temp, borrowed_amount_temp);
        let (new_leverage) = Math64x61_div(total_value, margin_amount_temp);
        let (new_leverage_rounded) = Math64x61_round(new_leverage, 6);
        let (new_pnl) = Math64x61_add(position_details.realized_pnl, trading_fee);
        let (margin_amount_rounded) = Math64x61_round(
            margin_amount_temp, collateral_token_decimal_
        );
        let (borrowed_amount_rounded) = Math64x61_round(
            borrowed_amount_temp, collateral_token_decimal_
        );

        // Create a new struct with the updated details
        assert updated_position_details = PositionDetails(
            avg_execution_price=average_execution_price_rounded,
            position_size=new_position_size,
            margin_amount=margin_amount_rounded,
            borrowed_amount=borrowed_amount_rounded,
            leverage=new_leverage_rounded,
            created_timestamp=created_timestamp,
            modified_timestamp=current_timestamp,
            realized_pnl=new_pnl,
        );

        assert updated_liquidatable_position = LiquidatablePosition(
            market_id=0, direction=0, amount_to_be_sold=0, liquidatable=0
        );

        assert pnl = trading_fee;
        assert opening_fee = trading_fee;
        assert current_open_interest = quantity_to_execute;
        assert is_liquidation = FALSE;

        let (new_margin_locked) = Math64x61_add(current_margin_locked, margin_lock_amount);
        assert updated_margin_locked = new_margin_locked;

        local is_final;
        if ([request_list_].time_in_force == IoC) {
            assert is_final = TRUE;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            let (is_final_temp) = Math64x61_is_equal(
                new_position_size, [request_list_].quantity, asset_token_decimal_
            );
            assert is_final = is_final_temp;
            tempvar range_check_ptr = range_check_ptr;
        }

        assert execution_details = ExecutionDetails(
            order_id=[request_list_].order_id,
            direction=[request_list_].direction,
            size=quantity_to_execute,
            order_type=[request_list_].order_type,
            order_side=[request_list_].side,
            execution_price=execution_price,
            pnl=pnl,
            side=current_order_side,
            opening_fee=trading_fee,
            is_final=is_final,
        );

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    } else {
        // Close order
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
        );

        // Calculate the new leverage if it's a deleveraging order
        local new_leverage;

        let (new_position_size) = Math64x61_sub(
            position_details.position_size, quantity_to_execute
        );

        // Check if it's liq/delveraging order
        let is_liq = is_le(LIQUIDATION_ORDER, [request_list_].order_type);

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        if (is_liq == TRUE) {
            let (updated_amount) = Math64x61_sub(
                liq_position.amount_to_be_sold, quantity_to_execute
            );

            let (is_equal_zero) = Math64x61_is_equal(updated_amount, 0, 6);  // Double check precision
            if (is_equal_zero == TRUE) {
                assert updated_liquidatable_position = LiquidatablePosition(
                    market_id=0, direction=0, amount_to_be_sold=0, liquidatable=0
                );
            } else {
                assert updated_liquidatable_position = LiquidatablePosition(
                    market_id=liq_position.market_id,
                    direction=liq_position.direction,
                    amount_to_be_sold=updated_amount,
                    liquidatable=liq_position.liquidatable,
                );
            }

            // If it's a deleveraging order, calculate the new leverage
            if ([request_list_].order_type == DELEVERAGING_ORDER) {
                // Error Handling: Position not marked as 'deleveragable'
                if (liq_position.liquidatable == TRUE) {
                    local error_code;
                    local error_order_id;
                    local error_param;

                    if (request_list_len_ == 1) {
                        with_attr error_message("526: {order_id} {quantity_to_execute}") {
                            assert 1 = 0;
                        }
                    } else {
                        if (error_order_id_ == 0) {
                            assert error_code = 526;
                            assert error_order_id = order_id;
                            assert error_param = quantity_to_execute;
                        } else {
                            assert error_code = error_code_;
                            assert error_order_id = error_order_id_;
                            assert error_param = error_param_;
                        }
                    }
                    // Call the account contract to reject the order
                    IAccountManager.execute_order(
                        contract_address=[request_list_].user_address,
                        batch_id_=batch_id_,
                        market_id_=market_id_,
                        collateral_id_=collateral_id_,
                        execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                        updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
                        updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
                        updated_margin_locked_=0,
                        updated_portion_executed_=0,
                        market_array_update_=0,
                        is_liquidation_=0,
                        error_message_=526,
                        error_param_1_=0,
                    );

                    return process_and_execute_orders_recurse(
                        batch_id_=batch_id_,
                        taker_locked_quantity_=taker_locked_quantity_,
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
                        total_order_volume_=total_order_volume_,
                        taker_execution_price_=taker_execution_price_,
                        open_interest_=open_interest_,
                        oracle_price_=oracle_price_,
                        error_order_id_=error_order_id,
                        error_code_=error_code,
                        error_param_=error_param,
                    );
                }

                let (total_value) = Math64x61_add(margin_amount_temp, borrowed_amount_temp);
                let (leverage_) = Math64x61_div(total_value, margin_amount_temp);
                let (leverage_rounded) = Math64x61_round(leverage_, 6);
                assert new_leverage = leverage_rounded;
                assert updated_margin_locked = current_margin_locked;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            } else {
                // Error Handling: Position not marked as 'liquidatable'
                if (liq_position.liquidatable == FALSE) {
                    local error_code;
                    local error_order_id;
                    local error_param;

                    if (request_list_len_ == 1) {
                        with_attr error_message("527: {order_id} {quantity_to_execute}") {
                            assert 1 = 0;
                        }
                    } else {
                        if (error_order_id_ == 0) {
                            assert error_code = 527;
                            assert error_order_id = order_id;
                            assert error_param = quantity_to_execute;
                        } else {
                            assert error_code = error_code_;
                            assert error_order_id = error_order_id_;
                            assert error_param = error_param_;
                        }
                    }

                    // Call the account contract to reject the order
                    IAccountManager.execute_order(
                        contract_address=[request_list_].user_address,
                        batch_id_=batch_id_,
                        market_id_=market_id_,
                        collateral_id_=collateral_id_,
                        execution_details_=ExecutionDetails(order_id, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                        updated_position_details_=PositionDetails(0, 0, 0, 0, 0, 0, 0, 0),
                        updated_liquidatable_position_=LiquidatablePosition(0, 0, 0, 0),
                        updated_margin_locked_=0,
                        updated_portion_executed_=0,
                        market_array_update_=0,
                        is_liquidation_=0,
                        error_message_=527,
                        error_param_1_=0,
                    );

                    return process_and_execute_orders_recurse(
                        batch_id_=batch_id_,
                        taker_locked_quantity_=taker_locked_quantity_,
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
                        total_order_volume_=total_order_volume_,
                        taker_execution_price_=taker_execution_price_,
                        open_interest_=open_interest_,
                        oracle_price_=oracle_price_,
                        error_order_id_=error_order_id,
                        error_code_=error_code,
                        error_param_=error_param,
                    );
                }

                let (new_margin_locked) = Math64x61_sub(
                    current_margin_locked, margin_unlock_amount
                );

                assert new_leverage = position_details.leverage;
                assert updated_margin_locked = new_margin_locked;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }
        } else {
            assert new_leverage = position_details.leverage;

            let (new_margin_locked) = Math64x61_sub(current_margin_locked, margin_unlock_amount);

            assert updated_margin_locked = new_margin_locked;

            if (liq_position.amount_to_be_sold == 0) {
                assert updated_liquidatable_position = LiquidatablePosition(
                    market_id=0, direction=0, amount_to_be_sold=0, liquidatable=0
                );

                tempvar syscall_ptr = syscall_ptr;
                tempvar range_check_ptr = range_check_ptr;
            } else {
                if (liq_position.market_id == market_id_) {
                    if (liq_position.direction == [request_list_].direction) {
                        let (new_amount_to_be_sold) = Math64x61_sub(
                            liq_position.amount_to_be_sold, quantity_to_execute
                        );
                        assert updated_liquidatable_position = LiquidatablePosition(
                            market_id=liq_position.market_id,
                            direction=liq_position.direction,
                            amount_to_be_sold=new_amount_to_be_sold,
                            liquidatable=liq_position.liquidatable,
                        );

                        tempvar syscall_ptr = syscall_ptr;
                        tempvar range_check_ptr = range_check_ptr;
                    } else {
                        assert updated_liquidatable_position = LiquidatablePosition(
                            market_id=0, direction=0, amount_to_be_sold=0, liquidatable=0
                        );

                        tempvar syscall_ptr = syscall_ptr;
                        tempvar range_check_ptr = range_check_ptr;
                    }
                } else {
                    assert updated_liquidatable_position = LiquidatablePosition(
                        market_id=0, direction=0, amount_to_be_sold=0, liquidatable=0
                    );

                    tempvar syscall_ptr = syscall_ptr;
                    tempvar range_check_ptr = range_check_ptr;
                }
            }
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        // Check if the current position size is 0
        let (is_zero_current_position) = Math64x61_is_equal(
            position_details.position_size, 0, asset_token_decimal_
        );

        // If yes, fetch the opposite position
        if (is_zero_current_position == TRUE) {
            let (opposite_direction: felt) = get_opposite(
                side_or_direction_=[request_list_].direction
            );
            let (opposite_position: PositionDetails) = IAccountManager.get_position_data(
                contract_address=[request_list_].user_address,
                market_id_=market_id_,
                direction_=opposite_direction,
            );

            // Check if the opposite position's size is 0
            let (is_zero_opposite_position) = Math64x61_is_equal(
                opposite_position.position_size, 0, asset_token_decimal_
            );

            // If yes, we need to remove this market from the array
            if (is_zero_opposite_position == TRUE) {
                assert market_array_update = 2;
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
                // If not, we do nothing
            } else {
                assert market_array_update = 0;
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }

            // updated position details
            assert updated_position_details = PositionDetails(
                avg_execution_price=0,
                position_size=0,
                margin_amount=0,
                borrowed_amount=0,
                leverage=0,
                created_timestamp=0,
                modified_timestamp=0,
                realized_pnl=0,
            );

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            let (current_pnl: felt) = Math64x61_add(position_details.realized_pnl, realized_pnl);
            let (margin_amount_rounded) = Math64x61_round(
                margin_amount_temp, collateral_token_decimal_
            );
            let (borrowed_amount_rounded) = Math64x61_round(
                borrowed_amount_temp, collateral_token_decimal_
            );

            // Round off the average execution price of the position
            let (average_execution_price_rounded) = Math64x61_round(
                average_execution_price_temp, collateral_token_decimal_
            );

            // Create a new struct with the updated details
            assert updated_position_details = PositionDetails(
                avg_execution_price=average_execution_price_rounded,
                position_size=new_position_size,
                margin_amount=margin_amount_rounded,
                borrowed_amount=borrowed_amount_rounded,
                leverage=new_leverage,
                created_timestamp=position_details.created_timestamp,
                modified_timestamp=current_timestamp,
                realized_pnl=current_pnl,
            );

            assert market_array_update = 0;

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }

        assert pnl = realized_pnl;
        assert opening_fee = 0;
        assert current_open_interest = 0 - quantity_to_execute;
        assert is_liquidation = is_liq;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;

        local is_final;
        if ([request_list_].time_in_force == IoC) {
            assert is_final = TRUE;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            let (current_available_position) = Math64x61_min(
                position_details.position_size, [request_list_].quantity
            );
            let (is_final_temp) = Math64x61_is_le(
                current_available_position, new_position_size, asset_token_decimal_
            );
            assert is_final = is_final_temp;
            tempvar range_check_ptr = range_check_ptr;
        }

        assert execution_details = ExecutionDetails(
            order_id=[request_list_].order_id,
            direction=[request_list_].direction,
            size=quantity_to_execute,
            order_type=[request_list_].order_type,
            order_side=[request_list_].side,
            execution_price=execution_price,
            pnl=realized_pnl,
            side=current_order_side,
            opening_fee=0,
            is_final=is_final,
        );

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    }

    let (new_portion_executed) = Math64x61_add(order_portion_executed, quantity_to_execute);

    if ([request_list_].time_in_force == IoC) {
        // Update the portion executed to request.quantity if it's an IoC order
        assert updated_portion_executed = [request_list_].quantity;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
    } else {
        // Update the portion executed
        assert updated_portion_executed = new_portion_executed;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
    }

    // Call the account contract to initialize the order
    IAccountManager.execute_order(
        contract_address=[request_list_].user_address,
        batch_id_=batch_id_,
        market_id_=market_id_,
        collateral_id_=collateral_id_,
        execution_details_=execution_details,
        updated_position_details_=updated_position_details,
        updated_liquidatable_position_=updated_liquidatable_position,
        updated_margin_locked_=updated_margin_locked,
        updated_portion_executed_=updated_portion_executed,
        market_array_update_=market_array_update,
        is_liquidation_=is_liquidation,
        error_message_=0,
        error_param_1_=0,
    );

    let (new_open_interest) = Math64x61_add(open_interest_, current_open_interest);

    return process_and_execute_orders_recurse(
        batch_id_=batch_id_,
        taker_locked_quantity_=taker_locked_quantity_,
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
        total_order_volume_=new_total_order_volume,
        taker_execution_price_=execution_price,
        open_interest_=new_open_interest,
        oracle_price_=oracle_price_,
        error_order_id_=error_order_id_,
        error_code_=error_code_,
        error_param_=error_param_,
    );
}

// @notice Internal function to validate maker orders
// @param maker1_direction_ - Direction of first maker order
// @param maker1_side_ - Side of first maker order
// @param current_direction_ - Direction of current maker order
// @param current_side_ -  Side of current maker order
// @returns is_error - True if there is an error in the direction of the maker; else false
func validate_maker{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    maker1_direction_: felt, maker1_side_: felt, current_direction_: felt, current_side_: felt
) -> (is_error: felt) {
    alloc_locals;
    let (local opposite_direction) = get_opposite(maker1_direction_);
    let (local opposite_side) = get_opposite(maker1_side_);
    if (current_direction_ == maker1_direction_) {
        if (current_side_ == maker1_side_) {
            return (FALSE,);
        }
    }

    if (current_direction_ == opposite_direction) {
        if (current_side_ == opposite_side) {
            return (FALSE,);
        }
    }

    return (TRUE,);
}

// @notice Internal function to validate taker orders
// @param maker1_direction_ - Direction of first maker order
// @param maker1_side_ - Side of first maker order
// @param current_direction_ - Direction of current maker order
// @param current_side_ -  Side of current maker order
// @returns is_error - True if there is an error in the direction of the taker; else false
func validate_taker{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    maker1_direction_: felt, maker1_side_: felt, current_direction_: felt, current_side_: felt
) -> (is_error: felt) {
    alloc_locals;
    let (local opposite_direction) = get_opposite(maker1_direction_);
    let (local opposite_side) = get_opposite(maker1_side_);
    if (current_direction_ == maker1_direction_) {
        if (current_side_ == opposite_side) {
            return (FALSE,);
        }
    }

    if (current_direction_ == opposite_direction) {
        if (current_side_ == maker1_side_) {
            return (FALSE,);
        }
    }

    return (TRUE,);
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

// @notice Internal function to check for hash collisions
// @param order_id - Order ID of the request
// @param order_hash - Hash of the corresponding order
func order_hash_check{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_id_: felt, order_hash_: felt
) -> (is_error: felt) {
    // Get the hash of the order associated with the order_id
    let (existing_hash) = order_id_mapping.read(order_id=order_id_);
    // If the hash isn't stored in the contract yet
    if (existing_hash == 0) {
        order_id_mapping.write(order_id=order_id_, value=order_hash_);
        return (FALSE,);
    } else {
        if (existing_hash == order_hash_) {
            return (FALSE,);
        } else {
            return (TRUE,);
        }
    }
}

// @notice view function which checks the signature passed is valid
// @param hash - Hash of the order to check against
// @param signature - Signature passed to the contract to check against
// @param liquidator_address_ - Address of the liquidator
// @return reverts, if there is an error
@view
func is_valid_signature_order{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*
}(hash: felt, signature: Signature, liquidator_address_: felt, user_public_key_: felt) -> () {
    let sig_r = signature.r_value;
    let sig_s = signature.s_value;

    if (liquidator_address_ == 0) {
        verify_ecdsa_signature(
            message=hash, public_key=user_public_key_, signature_r=sig_r, signature_s=sig_s
        );
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    } else {
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    }
    return ();
}

// @notice Internal function to hash the order parameters
// @param orderRequest - Struct of order request to hash
// @param res - Hash of the details
func hash_order{pedersen_ptr: HashBuiltin*}(orderRequest: felt*) -> (res: felt) {
    let hash_ptr = pedersen_ptr;
    // let orderRequestPointer: OrderRequest* = &orderRequest;
    with hash_ptr {
        let (hash_state_ptr) = hash_init();
        let (hash_state_ptr) = hash_update(hash_state_ptr, orderRequest, 11);
        let (res) = hash_finalize(hash_state_ptr);
        let pedersen_ptr = hash_ptr;
        return (res=res);
    }
}
