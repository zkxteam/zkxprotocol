%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.hash_state import hash_finalize, hash_init, hash_update
from starkware.cairo.common.math import abs_value, assert_le, assert_lt, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.starknet.common.syscalls import emit_event, get_block_timestamp

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
    IoC,
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
    ExecutionDetails,
    LiquidatablePosition,
    Market,
    MultipleOrder,
    OrderRequest,
    PositionDetails,
    PositionDetailsForRiskManagement,
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
    Math64x61_assert_le,
    Math64x61_div,
    Math64x61_is_equal,
    Math64x61_is_le,
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

    // Get the index of the Taker order
    let last_index = request_list_len - 1;

    let (initial_taker_locked: felt) = find_initial_taker_locked(
        asset_token_decimal_=asset.token_decimal,
        request_=request_list[last_index],
        quantity_locked_=quantity_locked_,
    );

    let (is_zero_quantity) = Math64x61_is_equal(initial_taker_locked, 0, 6);
    with_attr error_message("0523: {quantity_locked_} {0}") {
        assert is_zero_quantity = 0;
    }

    // Recursively loop through the orders in the batch
    let (taker_execution_price: felt, open_interest: felt) = process_and_execute_orders_recurse(
        original_quantity_locked_=initial_taker_locked,
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
        trader_stats_list_=trader_stats_list,
        total_order_volume_=0,
        taker_execution_price=0,
        open_interest_=0,
        oracle_price_=oracle_price_,
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

    // // Record TradingStats
    // ITradingStats.record_trade_batch_stats(
    //     contract_address=trading_stats_address,
    //     market_id_=market_id_,
    //     execution_price_64x61_=taker_execution_price,
    //     request_list_len=request_list_len,
    //     request_list=request_list,
    //     trader_stats_list_len=request_list_len,
    //     trader_stats_list=trader_stats_list,
    //     executed_sizes_list_len=request_list_len,
    //     executed_sizes_list=execution_sizes,
    //     open_interest_=open_interest,
    // );

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
// @returns quantity_to_execute_final - Calculated quantity to execute
func get_quantity_to_execute{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_portion_executed_: felt,
    position_details_: PositionDetails,
    asset_token_decimal_: felt,
    request_: MultipleOrder,
    quantity_remaining_: felt,
) -> (quantity_to_execute_final: felt) {
    alloc_locals;
    local quantity_to_execute;
    local quantity_to_execute_final;

    // Get min of remaining quantity and the order quantity
    let (executable_quantity: felt) = Math64x61_sub(request_.quantity, order_portion_executed_);
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
        let (cmp_res) = Math64x61_is_le(
            quantity_to_execute, position_details_.position_size, asset_token_decimal_
        );

        if (cmp_res == FALSE) {
            quantity_to_execute_final = position_details_.position_size;
        } else {
            quantity_to_execute_final = quantity_to_execute;
        }

        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        quantity_to_execute_final = quantity_to_execute;

        tempvar syscall_ptr = syscall_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    return (quantity_to_execute_final,);
}

// @notice Internal function to adjust and calculate the quantity locked and execution sizes
// @param asset_token_decimal_ - Number of decimals for the asset
// @param request_list_len_ - Length of the requests list
// @param request_list_ - Request list of orders
// @param quantity_locked_ - Original quantity lokcked of the batch
func find_initial_taker_locked{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_token_decimal_: felt, request_: MultipleOrder, quantity_locked_: felt
) -> (taker_quantity_to_execute: felt) {
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

    // Adjust the quantity to execute on the taker side
    let (taker_quantity_to_execute) = get_quantity_to_execute(
        order_portion_executed_=order_portion_executed,
        position_details_=position_details,
        asset_token_decimal_=asset_token_decimal_,
        request_=request_,
        quantity_remaining_=quantity_locked_,
    );

    return (taker_quantity_to_execute,);
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
) -> (is_error: felt, error_message: felt) {
    alloc_locals;

    if (direction_ == LONG) {
        // if it's a long order
        if (side_ == BUY) {
            let (limit_price_check) = Math64x61_is_le(
                execution_price_, price_, collateral_token_decimal_
            );

            if (limit_price_check == FALSE) {
                // if it's a buy order
                return (TRUE, '0508');
            }
        } else {
            // if it's a sell order
            let (limit_price_check) = Math64x61_is_le(
                price_, execution_price_, collateral_token_decimal_
            );

            if (limit_price_check == FALSE) {
                return (TRUE, '0507');
            }
        }
        tempvar range_check_ptr = range_check_ptr;
    } else {
        // if it's a short order
        if (side_ == BUY) {
            // if it's a buy order
            let (limit_price_check) = Math64x61_is_le(
                price_, execution_price_, collateral_token_decimal_
            );

            if (limit_price_check == FALSE) {
                return (TRUE, '0507');
            }
        } else {
            // if it's a sell order
            let (limit_price_check) = Math64x61_is_le(
                price_, execution_price_, collateral_token_decimal_
            );

            if (limit_price_check == FALSE) {
                return (TRUE, '0507');
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
    is_error: felt,
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

    let (user_balance_check) = Math64x61_is_le(
        fees, user_available_balance, collateral_token_decimal_
    );

    if (user_balance_check == FALSE) {
        return (FALSE, user_available_balance, 0, 0, 0, 0, 0);
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
        contract_address=holding_address_, asset_id_=collateral_id_, amount=leveraged_order_value
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

    // Calculate pnl and net account value
    let (pnl) = Math64x61_mul(order_size_, diff);
    let (margin_plus_pnl_felt) = Math64x61_add(margin_amount, pnl);
    assert margin_plus_pnl = margin_plus_pnl_felt;

    // Total value of the asset at current price
    let (leveraged_amount_out) = Math64x61_mul(order_size_, actual_execution_price);

    // Calculate the amount that needs to be returned to liquidity fund
    let (ratio_of_position) = Math64x61_div(order_size_, current_position.position_size);
    let (borrowed_amount_to_be_returned) = Math64x61_mul(borrowed_amount, ratio_of_position);
    let (local margin_amount_to_be_reduced) = Math64x61_mul(margin_amount, ratio_of_position);
    local margin_amount_open_64x61;

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
    IHolding.withdraw(
        contract_address=holding_address_, asset_id_=collateral_id_, amount=leveraged_amount_out
    );

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

    if (is_underwater == TRUE) {
        // If yes, deduct the difference from user's balance; balance can go negative
        // Absolute value of the acc value
        let amount_to_transfer_from = abs_value(margin_plus_pnl);

        let (
            is_liquidation: felt,
            total_margin: felt,
            available_margin: felt,
            unrealized_pnl_sum: felt,
            maintenance_margin_requirement: felt,
            least_collateral_ratio: felt,
            least_collateral_ratio_position: PositionDetailsForRiskManagement,
            least_collateral_ratio_position_asset_price: felt,
        ) = IAccountManager.get_margin_info(
            contract_address=order_.user_address,
            asset_id_=collateral_id_,
            new_position_maintanence_requirement_=0,
            new_position_margin_=0,
        );

        // Check if the user's balance can cover the deficit
        let (balance_check) = Math64x61_is_le(
            amount_to_transfer_from, available_margin, collateral_token_decimal_
        );
        if (balance_check == FALSE) {
            let (balance_less_than_zero_res) = Math64x61_is_le(
                available_margin, 0, collateral_token_decimal_
            );
            if (balance_less_than_zero_res == TRUE) {
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
                    amount_to_transfer_from, available_margin
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

        // Retrieve locked_margin from the user account
        let (total_amount_to_transfer_from) = Math64x61_add(
            amount_to_transfer_from, margin_amount_to_be_reduced
        );
        IAccountManager.transfer_from(
            contract_address=order_.user_address,
            asset_id_=collateral_id_,
            market_id_=market_id_,
            amount_=total_amount_to_transfer_from,
            invoked_for_='holding',
        );

        let (signed_realized_pnl) = Math64x61_mul(amount_to_transfer_from, NEGATIVE_ONE);
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
// @return res - returns the net sum of the orders do far
// @return trader_stats_list_len - length of the trader fee list so far
// @return open_interest - open interest corresponding to the trade batch
func process_and_execute_orders_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*
}(
    original_quantity_locked_: felt,
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
    trader_stats_list_: TraderStats*,
    total_order_volume_: felt,
    taker_execution_price: felt,
    open_interest_: felt,
    oracle_price_: felt,
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
    local updated_portion_executed;
    local opening_fee;
    local updated_position_details: PositionDetails;
    local execution_details: ExecutionDetails;
    local is_final;
    local pnl;

    // Local variable for setting the error
    local error_message;
    local error_param_1;
    local error_param_2;

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

    // Error Handling: User is not registered
    // check that the user account is present in account registry (and thus that it was deployed by zkx)
    let (is_registered) = IAccountRegistry.is_registered_user(
        contract_address=account_registry_address_, address_=user_address
    );
    if (is_registered == FALSE) {
        assert error_message = '0510';
        assert error_param_1 = order_id;
        assert error_param_2 = user_address;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        jmp error_handling;
    }

    // Error Handling: Quantity is less than the one set for the market
    let (size_check) = Math64x61_is_le(
        min_quantity_, [request_list_].quantity, asset_token_decimal_
    );
    if (size_check == FALSE) {
        assert error_message = '0505';
        assert error_param_1 = [request_list_].order_id;
        assert error_param_2 = quantity_order;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        jmp error_handling;
    }

    // Error Handling: Wrong market passed for the order
    if ([request_list_].market_id != market_id_) {
        assert error_message = '0504';
        assert error_param_1 = [request_list_].order_id;
        assert error_param_2 = market_id_order;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        jmp error_handling;
    }

    // Error Handling: Invalid leverage; leverage < minimum
    let (leverage_min_check) = Math64x61_is_le(
        LEVERAGE_ONE, [request_list_].leverage, asset_token_decimal_
    );
    if (leverage_min_check == FALSE) {
        assert error_message = '0503';
        assert error_param_1 = [request_list_].order_id;
        assert error_param_2 = leverage;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        jmp error_handling;
    }

    // Invalid leverage; leverage > maximum
    let (leverage_max_check) = Math64x61_is_le(
        [request_list_].leverage, max_leverage_, asset_token_decimal_
    );
    if (leverage_min_check == FALSE) {
        assert error_message = '0502';
        assert error_param_1 = [request_list_].order_id;
        assert error_param_2 = leverage;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        jmp error_handling;
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

    let (user_public_key, _) = IAccountManager.get_public_key(
        contract_address=[request_list_].user_address
    );

    local market_array_update;
    local updated_margin_locked;
    local updated_liquidatable_position: LiquidatablePosition;
    local updated_portion_executed;
    local current_portion_executed;
    local is_liquidation;
    local average_execution_price_rounded;

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

    // Code brought in from AccountManager
    // hash the parameters
    let (hash) = hash_order(temp_order_request);

    // Check for hash collision
    let (hash_error) = order_hash_check(order_id_=[request_list_].order_id, order_hash_=hash);

    if (hash_error == TRUE) {
        assert error_message = '0536';
        assert error_param_1 = [request_list_].order_id;
        assert error_param_2 = hash;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        jmp error_handling;
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
        let (is_zero_quantity) = Math64x61_is_equal(quantity_to_execute, 0, 6);
        with_attr error_message("0524: {original_quantity_locked} {0}") {
            assert is_zero_quantity = 0;
        }

        // Direction Check
        let (is_error) = validate_taker(
            order_id,
            maker1_direction_,
            maker1_side_,
            [request_list_].direction,
            [request_list_].side,
        );

        if (is_error == TRUE) {
            assert error_message = '0513';
            assert error_param_1 = [request_list_].order_id;
            assert error_param_2 = [request_list_].direction;

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;

            jmp error_handling;
        }

        // Error Handling: A Taker order cannot be a post only order
        if ([request_list_].post_only == TRUE) {
            assert error_message = '0515';
            assert error_param_1 = [request_list_].order_id;
            assert error_param_2 = current_index;

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;

            jmp error_handling;
        }

        local taker_quantity;
        assert taker_quantity = quantity_executed_;
        // Check for F&K type of orders; they must only be filled completely or rejected
        if ([request_list_].time_in_force == FoK) {
            let (diff_check) = Math64x61_sub([request_list_].quantity, taker_quantity);

            // Error Handling: A Taker order cannot be a post only order
            if (diff_check == FALSE) {
                assert error_message = '0516';
                assert error_param_1 = [request_list_].order_id;
                assert error_param_2 = taker_quantity;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;

                jmp error_handling;
            }

            // Error Handling: A Taker order cannot be a post only order
            if ([request_list_].order_type != LIMIT_ORDER) {
                assert error_message = '0550';
                assert error_param_1 = [request_list_].order_id;
                assert error_param_2 = MARKET_ORDER;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;

                jmp error_handling;
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
        if ([request_list_].order_type == MARKET_ORDER) {
            local slippage;
            assert slippage = [request_list_].slippage;
            // Error Handling: Slippage of a market order cannot be 0
            if (slippage != 0) {
                assert error_message = '0521';
                assert error_param_1 = [request_list_].order_id;
                assert error_param_2 = slippage;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;

                jmp error_handling;
            }

            // Error Handling: A Taker order cannot be a post only order
            if (is_le(slippage, FIFTEEN_PERCENTAGE) == 1) {
                assert error_message = '0521';
                assert error_param_1 = [request_list_].order_id;
                assert error_param_2 = slippage;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;

                jmp error_handling;
            }

            let (is_error: felt) = check_within_slippage(
                order_id_=order_id,
                slippage_=slippage,
                oracle_price_=oracle_price_,
                execution_price_=execution_price,
                direction_=[request_list_].direction,
                side_=[request_list_].side,
                collateral_token_decimal_=collateral_token_decimal_,
            );
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            let (is_error_1: felt, error_message_1: felt) = check_limit_price(
                order_id_=order_id,
                price_=[request_list_].price,
                execution_price_=new_execution_price,
                direction_=[request_list_].direction,
                side_=[request_list_].side,
                collateral_token_decimal_=collateral_token_decimal_,
            );

            if (is_error_1 == TRUE) {
                assert error_message = error_message_1;
                assert error_param_1 = [request_list_].order_id;
                assert error_param_2 = execution_price;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;

                jmp error_handling;
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

        // Find quantity left to be executed
        let (quantity_remaining) = Math64x61_sub(taker_locked_quantity_, quantity_executed_);

        // Find quantity that needs to be executed for the current order
        let (quantity_to_execute_remaining) = get_quantity_to_execute(
            order_portion_executed_=order_portion_executed,
            position_details_=position_details,
            asset_token_decimal_=asset_token_decimal_,
            request_=[request_list_],
            quantity_remaining_=quantity_remaining,
        );

        // Check the direction of the maker
        let (is_error) = validate_maker(
            order_id,
            maker1_direction_,
            maker1_side_,
            [request_list_].direction,
            [request_list_].side,
        );

        if (is_error == TRUE) {
            assert error_message = '0512';
            assert error_param_1 = [request_list_].order_id;
            assert error_param_2 = [request_list_].direction;

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;

            jmp error_handling;
        }

        // Error Handling: A Taker order cannot be a post only order
        if ([request_list_].order_type != LIMIT_ORDER) {
            assert error_message = '0518';
            assert error_param_1 = [request_list_].order_id;
            assert error_param_2 = current_index;

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;

            jmp error_handling;
        }
        assert quantity_to_execute = quantity_to_execute_remaining;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        // Send to AccountManager to emit an event in case the execution_price is 0
        if (quantity_to_execute == 0) {
            assert updated_liquidatable_position = LiquidatablePosition(
                market_id=0, direction=0, amount_to_be_sold=0, liquidatable=0
            );

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

            assert execution_details = ExecutionDetails(
                order_id=order_id,
                direction=[request_list_].direction,
                size=0,
                order_type=[request_list_].order_type,
                order_side=[request_list_].side,
                execution_price=[request_list_].price,
                pnl=0,
                side=MAKER,
                opening_fee=0,
                is_final=is_final,
            );

            let (is_final) = Math64x61_is_equal(
                order_portion_executed, [request_list_].quantity, asset_token_decimal_
            );

            assert updated_margin_locked = current_margin_locked;
            assert updated_portion_executed = order_portion_executed;
            assert market_array_update = 0;
            assert is_liquidation = 0;

            // Call the account contract to initialize the order
            IAccountManager.execute_order(
                contract_address=user_address,
                market_id_=market_id_,
                collateral_id_=collateral_id_,
                execution_details_=execution_details,
                updated_position_details_=updated_position_details,
                updated_liquidatable_position_=updated_liquidatable_position,
                updated_margin_locked_=updated_margin_locked,
                updated_portion_executed_=updated_portion_executed,
                market_array_update_=market_array_update,
                is_liquidation_=is_liquidation,
            );

            return process_and_execute_orders_recurse(
                original_quantity_locked_=original_quantity_locked_,
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
                trader_stats_list_=trader_stats_list_ + TraderStats.SIZE,
                total_order_volume_=total_order_volume_,
                taker_execution_price=0,
                open_interest_=open_interest_,
                oracle_price_=oracle_price_,
            );

            // tempvar syscall_ptr = syscall_ptr;
            // tempvar pedersen_ptr = pedersen_ptr;
            // tempvar range_check_ptr = range_check_ptr;
        }

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
            is_error: felt,
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
            trader_stats_list_=trader_stats_list_,
            side_=current_order_side,
        );

        // if (is_balance_error == TRUE) {
        //     assert error_message = '0501';
        //     assert error_param_1 = [request_list_].order_id;
        //     assert error_param_2 = user_available_balance;
        //     jmp error_handling;
        // }

        // Local variable to store the timestamp at which the position was opened
        local created_timestamp;

        // Round off the average execution price of the position
        let (average_execution_price_rounded_felt) = Math64x61_round(
            average_execution_price, collateral_token_decimal_
        );

        assert average_execution_price_rounded = average_execution_price_rounded_felt;

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
                contract_address=user_address, market_id_=market_id_, direction_=opposite_direction
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

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }

        // Calculate the updated position data
        let (new_position_size) = Math64x61_add(
            position_details.position_size, quantity_to_execute
        );
        let (total_value) = Math64x61_add(margin_amount_temp, borrowed_amount_temp);
        let (new_leverage) = Math64x61_div(total_value, margin_amount_temp);
        let (new_leverage_rounded) = Math64x61_round(new_leverage, 6);
        let (new_pnl) = Math64x61_add(position_details.realized_pnl, trading_fee);
        let (new_pnl_rounded) = Math64x61_round(new_pnl, collateral_token_decimal_);
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
            realized_pnl=new_pnl_rounded,
        );
        let (new_margin_locked) = Math64x61_add(current_margin_locked, margin_lock_update_amount);
        assert updated_margin_locked = new_margin_locked;

        let (new_portion_executed) = Math64x61_add(order_portion_executed, quantity_to_execute);

        let (is_final) = Math64x61_is_equal(
            order_portion_executed, [request_list_].quantity, asset_token_decimal_
        );

        assert execution_details = ExecutionDetails(
            order_id=order_id,
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

        assert updated_liquidatable_position = LiquidatablePosition(
            market_id=0, direction=0, amount_to_be_sold=0, liquidatable=0
        );

        assert pnl = trading_fee;
        assert opening_fee = trading_fee;
        assert current_open_interest = quantity_to_execute;
        assert margin_lock_update_amount = margin_lock_amount;
        assert current_portion_executed = new_portion_executed;
        assert is_liquidation = FALSE;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
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
            trader_stats_list_=trader_stats_list_,
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
            // If it's not a normal order, check if it satisfies the conditions to liquidate/deleverage
            let liq_position: LiquidatablePosition = IAccountManager.get_deleveragable_or_liquidatable_position(
                contract_address=user_address, collateral_id_=collateral_id_);

            // Error Handling: Wrong market for liquidation
            if (liq_position.market_id != market_id_) {
                assert error_message = '0531';
                assert error_param_1 = [request_list_].order_id;
                assert error_param_2 = market_id_;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;

                jmp error_handling;
            }

            // Error Handling: Wrong direction for liquidation
            if (liq_position.direction != [request_list_].direction) {
                assert error_message = '0532';
                assert error_param_1 = [request_list_].order_id;
                assert error_param_2 = [request_list_].direction;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;

                jmp error_handling;
            }

            // Error Handling: Size larger than marked one
            let (liquidatable_size_check) = Math64x61_is_le(
                quantity_to_execute, liq_position.amount_to_be_sold, asset_token_decimal_
            );
            if (liquidatable_size_check == FALSE) {
                assert error_message = '0533';
                assert error_param_1 = [request_list_].order_id;
                assert error_param_2 = quantity_to_execute;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;

                jmp error_handling;
            }

            let (updated_amount) = Math64x61_sub(
                liq_position.amount_to_be_sold, quantity_to_execute
            );

            local new_liquidatable_position: LiquidatablePosition;
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
                    assert error_message = '0534';
                    assert error_param_1 = [request_list_].order_id;
                    assert error_param_2 = quantity_to_execute;

                    tempvar syscall_ptr = syscall_ptr;
                    tempvar pedersen_ptr = pedersen_ptr;
                    tempvar range_check_ptr = range_check_ptr;
                    jmp error_handling;
                }

                let (total_value) = Math64x61_add(margin_amount, borrowed_amount);
                let (leverage_) = Math64x61_div(total_value, margin_amount);
                let (leverage_rounded) = Math64x61_round(leverage_, 6);
                assert new_leverage = leverage_rounded;
                assert updated_margin_locked = current_margin_locked;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            } else {
                // Error Handling: Position not marked as 'liquidatable'
                if (liq_position.liquidatable == FALSE) {
                    assert error_message = '0535';
                    assert error_param_1 = [request_list_].order_id;
                    assert error_param_2 = quantity_to_execute;

                    tempvar syscall_ptr = syscall_ptr;
                    tempvar pedersen_ptr = pedersen_ptr;
                    tempvar range_check_ptr = range_check_ptr;

                    jmp error_handling;
                }

                let (new_margin_locked) = Math64x61_sub(
                    current_margin_locked, margin_lock_update_amount
                );

                assert new_leverage = position_details.leverage;
                assert updated_margin_locked = new_margin_locked;

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }
        } else {
            assert new_leverage = position_details.leverage;

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        let (is_zero_current_position) = Math64x61_is_equal(
            new_position_size, 0, asset_token_decimal_
        );
        if (is_zero_current_position == TRUE) {
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

            if (is_zero_opposite_position == 1) {
                assert market_array_update = 2;
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            } else {
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
            let (current_pnl: felt) = Math64x61_add(position_details.realized_pnl, pnl);
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
                leverage=new_leverage,
                created_timestamp=position_details.created_timestamp,
                modified_timestamp=current_timestamp,
                realized_pnl=current_pnl,
            );

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }

        let (new_portion_executed) = Math64x61_add(order_portion_executed, quantity_to_execute);

        assert execution_details = ExecutionDetails(
            order_id=order_id,
            direction=[request_list_].direction,
            size=quantity_to_execute,
            order_type=[request_list_].order_type,
            order_side=[request_list_].side,
            execution_price=execution_price,
            pnl=pnl,
            side=current_order_side,
            opening_fee=0,
            is_final=is_final,
        );

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;

        assert current_open_interest = quantity_to_execute;
        assert margin_lock_update_amount = margin_unlock_amount;
        assert current_portion_executed = new_portion_executed;

        assert margin_amount = margin_amount_temp;
        assert borrowed_amount = borrowed_amount_temp;
        assert average_execution_price = average_execution_price_temp;
        assert pnl = realized_pnl;
        assert opening_fee = 0;
        assert current_open_interest = 0 - quantity_to_execute;
        assert margin_lock_update_amount = margin_unlock_amount;
        assert is_liquidation = is_liq;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    if ([request_list_].time_in_force == IoC) {
        // Update the portion executed to request.quantity if it's an IoC order
        updated_portion_executed = [request_list_].quantity;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
    } else {
        // Update the portion executed
        updated_portion_executed = current_portion_executed;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
    }

    // Call the account contract to initialize the order
    IAccountManager.execute_order(
        contract_address=user_address,
        market_id_=market_id_,
        collateral_id_=collateral_id_,
        execution_details_=execution_details,
        updated_position_details_=updated_position_details,
        updated_liquidatable_position_=updated_liquidatable_position,
        updated_margin_locked_=updated_margin_locked,
        updated_portion_executed_=updated_portion_executed,
        market_array_update_=market_array_update,
        is_liquidation_=is_liquidation,
    );

    let (new_open_interest) = Math64x61_add(open_interest_, current_open_interest);

    return process_and_execute_orders_recurse(
        original_quantity_locked_=original_quantity_locked_,
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
        trader_stats_list_=trader_stats_list_ + TraderStats.SIZE,
        total_order_volume_=new_total_order_volume,
        taker_execution_price=execution_price,
        open_interest_=new_open_interest,
        oracle_price_=oracle_price_,
    );

    error_handling:
    // Emit the event
    let (keys: felt*) = alloc();
    assert keys[0] = 'order_rejected';
    let (data: felt*) = alloc();
    assert data[0] = error_message;
    assert data[1] = error_param_1;
    assert data[2] = error_param_2;

    emit_event(1, keys, 3, data);

    return process_and_execute_orders_recurse(
        original_quantity_locked_=original_quantity_locked_,
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
        trader_stats_list_=trader_stats_list_,
        total_order_volume_=total_order_volume_,
        taker_execution_price=taker_execution_price,
        open_interest_=open_interest_,
        oracle_price_=oracle_price_,
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
) -> (is_error: felt) {
    alloc_locals;
    let (local opposite_direction) = get_opposite(maker1_direction_);
    let (local opposite_side) = get_opposite(maker1_side_);
    if (current_direction_ == maker1_direction_) {
        if (current_side_ == maker1_side_) {
            return (FALSE);
        }
    }

    if (current_direction_ == opposite_direction) {
        if (current_side_ == opposite_side) {
            return (FALSE);
        }
    }

    return (TRUE);
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
) -> (is_error: felt) {
    alloc_locals;
    let (local opposite_direction) = get_opposite(maker1_direction_);
    let (local opposite_side) = get_opposite(maker1_side_);
    if (current_direction_ == maker1_direction_) {
        if (current_side_ == opposite_side) {
            return (FALSE);
        }
    }

    if (current_direction_ == opposite_direction) {
        if (current_side_ == maker1_side_) {
            return (FALSE);
        }
    }

    return (TRUE);
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
        return (FALSE);
    }

    return (TRUE);
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
    alloc_locals;

    let sig_r = signature.r_value;
    let sig_s = signature.s_value;
    local pub_key;

    if (liquidator_address_ != 0) {
        // Verify whether call came from node operator
        let (_public_key) = IAccountLiquidator.getPublicKey(contract_address=liquidator_address_);
        pub_key = _public_key;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    } else {
        pub_key = user_public_key_;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    }

    verify_ecdsa_signature(message=hash, public_key=pub_key, signature_r=sig_r, signature_s=sig_s);
    return ();
}

// @notice Internal function to hash the order parameters
// @param orderRequest - Struct of order request to hash
// @param res - Hash of the details
func hash_order{pedersen_ptr: HashBuiltin*}(orderRequest: OrderRequest) -> (res: felt) {
    let hash_ptr = pedersen_ptr;
    with hash_ptr {
        let (hash_state_ptr) = hash_init();
        let (hash_state_ptr) = hash_update(hash_state_ptr, orderRequest, 11);
        let (res) = hash_finalize(hash_state_ptr);
        let pedersen_ptr = hash_ptr;
        return (res=res);
    }
}
