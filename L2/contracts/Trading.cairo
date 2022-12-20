%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math import (
    abs_value,
    assert_in_range,
    assert_le,
    assert_lt,
    assert_nn,
    assert_not_zero,
)
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.common.syscalls import get_block_timestamp

from contracts.Constants import (
    AccountRegistry_INDEX,
    AdminAuth_INDEX,
    Asset_INDEX,
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
    MasterAdmin_ACTION,
    SHORT,
    STOP_ORDER,
    TAKER,
    TradingFees_INDEX,
    TradingStats_INDEX,
)
from contracts.DataTypes import (
    Asset,
    Market,
    MarketPrice,
    MultipleOrder,
    OrderRequest,
    PositionDetails,
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
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import (
    Math64x61_add,
    Math64x61_div,
    Math64x61_mul,
    Math64x61_sub,
    Math64x61_ONE,
)

//############
// Constants #
//############
const LEVERAGE_ONE = 2305843009213693952;
const FIFTEEN_PERCENTAGE = 34587645138205409280;
const HUNDRED = 230584300921369395200;

// //////////
// Events //
// //////////

// Event emitted whenever a new market is added
@event
func trade_execution(address: felt, request: OrderRequest, market_id: felt, execution_price: felt) {
}

//##########
// Storage #
//##########

// Stores public key associated with an account
@storage_var
func threshold_percentage() -> (res: felt) {
}

// Stores if a batch id is executed
@storage_var
func batch_id_status(batch_id: felt) -> (res: felt) {
}

//##############
// Constructor #
//##############

// ////////
// View //
// ////////
@view
func get_batch_id_status{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    batch_id_: felt
) -> (status: felt) {
    alloc_locals;

    let (status: felt) = batch_id_status.read(batch_id=batch_id_);
    return (status,);
}

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

// ////////////
// External //
// ////////////

// @notice Function to set the threshold percentage can only be called by masterAdmin; all execution_prices must be +/-threshold percentage of oracle price
// @param new_percentage - New value of threshold percentage to be set in the contract
@external
func set_threshold_percentage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_percentage
) {
    with_attr error_message("Trading: Unauthorized") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    with_attr error_message("Trading: Invalid percentage passed") {
        assert_lt(0, new_percentage);
        assert_lt(new_percentage, FIFTEEN_PERCENTAGE);
    }
    threshold_percentage.write(value=new_percentage);
    return ();
}

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

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Calculate the timestamp
    let (current_timestamp) = get_block_timestamp();

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

    let (trader_stats_list: TraderStats*) = alloc();

    // check oracle price
    let (lower_limit: felt, upper_limit: felt) = get_price_range(oracle_price_=oracle_price_);

    // get collateral id
    let (asset_id: felt, collateral_id: felt) = IMarkets.get_asset_collateral_from_market(
        contract_address=market_address, market_id_=market_id_
    );

    // Recursively loop through the orders in the batch
    let (trader_stats_list_len, taker_execution_price) = check_and_execute(
        quantity_locked_=quantity_locked_,
        market_id_=market_id_,
        collateral_id_=collateral_id,
        lower_limit_=lower_limit,
        upper_limit_=upper_limit,
        orders_len_=request_list_len,
        request_list_len_=request_list_len,
        request_list_=request_list,
        quantity_executed_=0,
        account_registry_address_=account_registry_address,
        asset_address_=asset_address,
        market_address_=market_address,
        holding_address_=holding_address,
        trading_fees_address_=trading_fees_address,
        fees_balance_address_=fees_balance_address,
        liquidate_address_=liquidate_address,
        liquidity_fund_address_=liquidity_fund_address,
        insurance_fund_address_=insurance_fund_address,
        max_leverage_=0,
        min_quantity_=0,
        maker_direction_=0,
        trader_stats_list_len_=0,
        trader_stats_list_=trader_stats_list,
        total_order_volume_=0,
        taker_execution_price=0,
    );

    // /// Set Market Price /////
    // Get Market from the corresponding Id
    let (market: Market) = IMarkets.get_market(
        contract_address=market_address, market_id_=market_id_
    );
    tempvar ttl = market.ttl;

    // Get Market price for the corresponding market Id
    let (market_prices: MarketPrice) = IMarketPrices.get_market_price(
        contract_address=market_prices_address, id=market_id_
    );

    tempvar timestamp = market_prices.timestamp;
    tempvar time_difference = current_timestamp - timestamp;
    let status = is_le(time_difference, ttl);

    // update market price
    if (status == FALSE) {
        IMarketPrices.update_market_price(
            contract_address=market_prices_address, id=market_id_, price=taker_execution_price
        );
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    tempvar syscall_ptr = syscall_ptr;
    tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
    tempvar range_check_ptr = range_check_ptr;

    // // Record TradingStats
    // ITradingStats.record_trade_batch_stats(
    //     contract_address=trading_stats_address,
    //     pair_id_=market_id_,
    //     order_size_64x61_=quantity_locked_,
    //     execution_price_64x61_=taker_execution_price,
    //     request_list_len=request_list_len,
    //     request_list=request_list,
    //     trader_stats_list_len=trader_stats_list_len,
    //     trader_stats_list=trader_stats_list,
    // );

    batch_id_status.write(batch_id=batch_id_, value=1);

    return ();
}

// ////////////
// Internal //
// ////////////

func check_within_slippage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    slippage_: felt, price_: felt, execution_price_: felt
) {
    // To remove
    alloc_locals;
    with_attr error_message("Trading: Slippage percentage must be positive & below 15") {
        assert_nn(slippage_);
        assert_le(slippage_, FIFTEEN_PERCENTAGE);
    }

    let (percentage) = Math64x61_div(slippage_, HUNDRED);
    let (threshold) = Math64x61_mul(percentage, price_);

    let (lower_limit: felt) = Math64x61_sub(price_, threshold);
    let (upper_limit: felt) = Math64x61_add(price_, threshold);

    local lower_limit_;
    assert lower_limit_ = lower_limit;
    with_attr error_message("Trading: High slippage for execution price") {
        assert_in_range(execution_price_, lower_limit, upper_limit);
    }
    return ();
}

func check_limit_price{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    price_: felt, execution_price_: felt, direction_: felt
) {
    // if it's a limit order
    if (direction_ == LONG) {
        // if it's a long order
        with_attr error_message("Trading: Bad long limit order") {
            assert_le(execution_price_, price_);
        }
        tempvar range_check_ptr = range_check_ptr;
    } else {
        // if it's a short order
        with_attr error_message("Trading: Bad short limit order") {
            assert_le(price_, execution_price_);
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

    // Get ccount Registry address
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    );

    // Get asset address
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

    // Get Fee balalnce address
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

// Internal Function to check if the price is fair for an order
// @param oracle_price - Mean of the oracle price passed by the Node network
// @returns lower_limit
// @returns upper_limit
func get_price_range{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    oracle_price_: felt
) -> (lower_limit: felt, upper_limit: felt) {
    let (current_threshold_percentage) = threshold_percentage.read();
    let (percentage) = Math64x61_div(current_threshold_percentage, HUNDRED);
    let (threshold) = Math64x61_mul(percentage, oracle_price_);

    let (lower_limit: felt) = Math64x61_sub(oracle_price_, threshold);
    let (upper_limit: felt) = Math64x61_add(oracle_price_, threshold);
    return (lower_limit, upper_limit);
}

// @notice Intenal function that processes open orders
// @param order_ - Order request
// @param execution_price_ - The price at which it got matched
// @param order_size_ - The size of the asset that got matched
// @param market_id_ - The market ID of the batch
// @param collateral_id_ - Collateral_id of all the orders in the batch
// @param trading_fees_address_ - Address of the Trading Fees contract
// @param liquidity_fund_address_ - Address of the Liquidity contract
// @param liquidate_address_ - Address of the Liquidate contract
// @param fees_balance_address_ - Address of the Fee Balance contract
// @param holding_address_ - Address of the Holding contract
// @param trader_stats_list_len_ - length of the trader fee list
// @param trader_stats_list_ - traders fee list
// @param current_index_ - Index of the order that is being processed
// @returns average_execution_price_open - Average Execution Price for the order
// @returns margin_amount_open - Margin amount for the order
// @returns borrowed_amount_open - Borrowed amount for the order
// @returns trader_stats_list_len - length of the trader fee list
func process_open_orders{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_: MultipleOrder,
    execution_price_: felt,
    order_size_: felt,
    market_id_: felt,
    collateral_id_: felt,
    trading_fees_address_: felt,
    liquidity_fund_address_: felt,
    liquidate_address_: felt,
    fees_balance_address_: felt,
    holding_address_: felt,
    trader_stats_list_len_: felt,
    trader_stats_list_: TraderStats*,
    current_index_: felt,
    side_: felt,
) -> (
    average_execution_price_open: felt,
    margin_amount_open: felt,
    borrowed_amount_open: felt,
    trader_stats_list_len: felt,
) {
    alloc_locals;

    local margin_amount_open;
    local borrowed_amount_open;
    local average_execution_price_open;

    // Get the fees from Trading Fee contract
    let (fees_rate) = ITradingFees.get_user_fee_and_discount(
        contract_address=trading_fees_address_, address_=order_.user_address, side_=side_
    );

    // Get order details
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

    // Calculate the total amount by adding fees
    let (order_value_with_fee_felt) = Math64x61_add(margin_order_value, fees);
    tempvar order_value_with_fee = order_value_with_fee_felt;

    // // Check if the position can be opened
    // ILiquidate.check_order_can_be_opened(
    //     contract_address=liquidate_address_,
    //     order=order_,
    //     size=order_size_,
    //     execution_price=execution_price_,
    // );

    // Error messages need local variables to be passed in params
    local user_address;
    assert user_address = order_.user_address;

    let (user_balance) = IAccountManager.get_balance(
        contract_address=order_.user_address, assetID_=collateral_id_
    );

    // User must be able to pay the amount
    with_attr error_message("Trading: Low Balance- {current_index_}") {
        assert_le(order_value_with_fee, user_balance);
    }

    // Deduct the amount from account contract
    IAccountManager.transfer_from(
        contract_address=order_.user_address, assetID_=collateral_id_, amount=order_value_with_fee
    );

    // Update the fees to be paid by user in fee balance contract
    IFeeBalance.update_fee_mapping(
        contract_address=fees_balance_address_,
        address=order_.user_address,
        assetID_=collateral_id_,
        fee_to_add=fees,
    );

    let (order_volume_64x61) = Math64x61_mul(order_size_, execution_price_);

    // Update Trader stats
    let element: TraderStats = TraderStats(order_.user_address, fees, order_volume_64x61, 0, 0, 0);
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
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Deposit the funds taken from the user and liquidity fund
    IHolding.deposit(
        contract_address=holding_address_, asset_id_=collateral_id_, amount=leveraged_order_value
    );

    return (
        average_execution_price_open,
        margin_amount_open,
        borrowed_amount_open,
        trader_stats_list_len_ + 1,
    );
}

// @notice Intenal function that processes close orders including Liquidation & Deleveraging
// @param order_ - Order request
// @param execution_price_ - The price at which it got matched
// @param order_size_ - The size of the asset that got matched
// @param market_id_ - The market ID of the batch
// @param collateral_id_ - Collateral_id of all the orders in the batch
// @param liquidity_fund_address_ - Address of the Liquidity contract
// @param insurance_fund_address - Address of the Insurance Fund contract
// @param holding_address_ - Address of the Holding contract
// @param trader_stats_list_len_ - length of the trader fee list
// @param trader_stats_list_ - traders fee list
// @param current_index_ - Index of the order that is being processed
// @returns average_execution_price_open - Average Execution Price for the order
// @returns margin_amount_open - Margin amount for the order
// @returns borrowed_amount_open - Borrowed amount for the order
func process_close_orders{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_: MultipleOrder,
    execution_price_: felt,
    order_size_: felt,
    market_id_: felt,
    collateral_id_: felt,
    liquidity_fund_address_: felt,
    insurance_fund_address_: felt,
    holding_address_: felt,
    trader_stats_list_len_: felt,
    trader_stats_list_: TraderStats*,
    current_index_: felt,
) -> (
    margin_amount_close: felt,
    borrowed_amount_close: felt,
    average_execution_price_close: felt,
    trader_stats_list_len: felt,
) {
    alloc_locals;

    local margin_amount_close;
    local borrowed_amount_close;
    local average_execution_price_close;

    // Get the direction of the position that is to be closed
    local parent_direction;

    if (order_.direction == LONG) {
        assert parent_direction = SHORT;
    } else {
        assert parent_direction = LONG;
    }

    // Get order details
    let (parent_position: PositionDetails) = IAccountManager.get_position_data(
        contract_address=order_.user_address, market_id_=market_id_, direction_=parent_direction
    );

    with_attr error_message("The parentPosition size cannot be 0- {current_index_}") {
        assert_not_zero(parent_position.position_size);
    }

    let margin_amount = parent_position.margin_amount;
    let borrowed_amount = parent_position.borrowed_amount;
    average_execution_price_close = parent_position.avg_execution_price;

    local diff;
    local actual_execution_price;
    local margin_plus_pnl;

    // current order is short order
    if (order_.direction == SHORT) {
        // Open order was a long order
        assert actual_execution_price = execution_price_;
        let (diff_felt) = Math64x61_sub(execution_price_, parent_position.avg_execution_price);
        assert diff = diff_felt;
    } else {
        // Open order was a short order
        let (diff_felt) = Math64x61_sub(parent_position.avg_execution_price, execution_price_);
        assert diff = diff_felt;
        let (actual_exexution_price_felt) = Math64x61_add(
            parent_position.avg_execution_price, diff
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
    let (percent_of_position) = Math64x61_div(order_size_, parent_position.position_size);
    let (borrowed_amount_to_be_returned) = Math64x61_mul(borrowed_amount, percent_of_position);
    let (margin_amount_to_be_reduced) = Math64x61_mul(margin_amount, percent_of_position);
    local margin_amount_open_64x61;

    // Calculate new values for margin and borrowed amounts
    if (order_.order_type == DELEVERAGING_ORDER) {
        let (borrowed_amount_close_felt) = Math64x61_sub(borrowed_amount, leveraged_amount_out);
        assert borrowed_amount_close = borrowed_amount_close_felt;
        margin_amount_close = margin_amount;
        margin_amount_open_64x61 = 0;
    } else {
        let (borrowed_amount_close_felt) = Math64x61_sub(
            borrowed_amount, borrowed_amount_to_be_returned
        );
        assert borrowed_amount_close = borrowed_amount_close_felt;

        let (margin_amount_close_felt) = Math64x61_sub(margin_amount, margin_amount_to_be_reduced);
        assert margin_amount_close = margin_amount_close_felt;
        margin_amount_open_64x61 = margin_amount_to_be_reduced;
    }

    let (order_volume_64x61) = Math64x61_mul(order_size_, execution_price_);

    // Update trader stats.
    // If close order is a deleveraging order, margin won't be reduced. So, we will record 0.
    // Else, we will record margin_to_be_reduced
    let element: TraderStats = TraderStats(
        order_.user_address, 0, order_volume_64x61, 1, pnl, margin_amount_open_64x61
    );
    assert [trader_stats_list_] = element;

    // Check if the position is to be liquidated
    let not_liquidation = is_le(order_.order_type, 3);

    // Deduct funds from holding contract
    IHolding.withdraw(
        contract_address=holding_address_, asset_id_=collateral_id_, amount=leveraged_amount_out
    );

    // If it's just a close order
    if (not_liquidation == TRUE) {
        // If no leverage is used
        // to64x61(1) == 2305843009213693952
        if (parent_position.leverage == LEVERAGE_ONE) {
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            ILiquidityFund.deposit(
                contract_address=liquidity_fund_address_,
                asset_id_=collateral_id_,
                amount=borrowed_amount_to_be_returned,
                position_id_=order_.order_id,
            );
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        // Check if the position is underwater
        let is_negative = is_le(margin_plus_pnl, 0);

        if (is_negative == TRUE) {
            // If yes, deduct the difference from user's balance, can go negative
            let (amount_to_transfer_from) = Math64x61_sub(
                leveraged_amount_out, borrowed_amount_to_be_returned
            );
            IAccountManager.transfer_from(
                contract_address=order_.user_address,
                assetID_=collateral_id_,
                amount=amount_to_transfer_from,
            );
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            // If not, transfer the remaining to user
            let (amount_to_transfer) = Math64x61_sub(
                leveraged_amount_out, borrowed_amount_to_be_returned
            );
            IAccountManager.transfer(
                contract_address=order_.user_address,
                assetID_=collateral_id_,
                amount=amount_to_transfer,
            );
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
    } else {
        // Liquidation order
        if (order_.order_type == LIQUIDATION_ORDER) {
            // Return the borrowed fund to the Liquidity fund
            ILiquidityFund.deposit(
                contract_address=liquidity_fund_address_,
                asset_id_=collateral_id_,
                amount=borrowed_amount_to_be_returned,
                position_id_=order_.order_id,
            );

            // Check if the account value for the position is negative
            let is_negative = is_le(margin_plus_pnl, 0);

            if (is_negative == TRUE) {
                // Absolute value of the acc value
                let deficit = abs_value(margin_plus_pnl);

                // Get the user balance
                let (user_balance) = IAccountManager.get_balance(
                    contract_address=order_.user_address, assetID_=collateral_id_
                );

                // Check if the user's balance can cover the deficit
                let is_payable = is_le(deficit, user_balance);

                if (is_payable == TRUE) {
                    // Transfer the full amount from the user
                    IAccountManager.transfer_from(
                        contract_address=order_.user_address,
                        assetID_=collateral_id_,
                        amount=deficit,
                    );

                    tempvar syscall_ptr = syscall_ptr;
                    tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                    tempvar range_check_ptr = range_check_ptr;
                } else {
                    // Transfer the partial amount from the user
                    IAccountManager.transfer_from(
                        contract_address=order_.user_address,
                        assetID_=collateral_id_,
                        amount=user_balance,
                    );

                    // Transfer the remaining amount from Insurance Fund
                    let (insurance_amount_claim) = Math64x61_sub(deficit, user_balance);
                    IInsuranceFund.withdraw(
                        contract_address=insurance_fund_address_,
                        asset_id_=collateral_id_,
                        amount=insurance_amount_claim,
                        position_id_=order_.order_id,
                    );

                    tempvar syscall_ptr = syscall_ptr;
                    tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                    tempvar range_check_ptr = range_check_ptr;
                }
            } else {
                // Deposit the user's remaining margin in Insurance Fund
                IInsuranceFund.deposit(
                    contract_address=insurance_fund_address_,
                    asset_id_=collateral_id_,
                    amount=margin_plus_pnl,
                    position_id_=order_.order_id,
                );

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }
        } else {
            // Deleveraging order
            with_attr error_message("Wrong order type passed") {
                assert order_.order_type = DELEVERAGING_ORDER;
            }
            // Return the borrowed fund to the Liquidity fund
            ILiquidityFund.deposit(
                contract_address=liquidity_fund_address_,
                asset_id_=collateral_id_,
                amount=leveraged_amount_out,
                position_id_=order_.order_id,
            );

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    return (
        average_execution_price_close,
        margin_amount_close,
        borrowed_amount_close,
        trader_stats_list_len_ + 1,
    );
}

// @notice Internal function called by execute_batch
// @param quantity_locked_ - Size of the order to be executed
// @param market_id_ - Market ID of the batch
// @param collateralID_ - Collateral ID of the batch to be set by the first order
// @param lower_limit_ - Lower threshold of the passed oracle price
// @param upper_limit_ - Upper threshold of the passed oracle price
// @param orders_len_ - Length fo the execute batch (to be used to calculate the index of each order)
// @param request_list_len_ - No of orders in the batch
// @param request_list_ - The batch of the orders
// @param quantity_executed_ - Quantity of maker orders executed so far
// @param account_registry_address_ - Address of the Account Registry contract
// @param asset_address_ - Address of the Asset contract
// @param market_address_ - Address of the Market contract
// @param holding_address_ - Address of the Holding contract
// @param trading_fees_address_ - Address of the Trading contract
// @param fees_balance_address_ - Address of the Fee Balance contract
// @param liquidate_address_ - Address of the Liquidate contract
// @param liquidity_fund_address_ - Address of the Liquidity Fund contract
// @param insurance_fund_address_ - Address of the Insurance Fund contract
// @param max_leverage_ - Maximum Leverage for the market set by the first order
// @param min_quantity_ - Minimum quantity for the market set by the first order
// @param maker_direction_ - Direction of the maker order
// @param trader_stats_list_len_ - length of the trader fee list
// @param trader_stats_list_ - This list contains trader addresses along with fee charged
// @param total_order_volume_ - This stores the sum of size*execution_price for each maker order
// @param taker_execution_price - The price to be stored for the market price in execute_batch
// @return res - returns the net sum of the orders do far
// @return trader_stats_list_len - returns the length of the trader fee list so far
func check_and_execute{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    quantity_locked_: felt,
    market_id_: felt,
    collateral_id_: felt,
    lower_limit_: felt,
    upper_limit_: felt,
    orders_len_: felt,
    request_list_len_: felt,
    request_list_: MultipleOrder*,
    quantity_executed_: felt,
    account_registry_address_: felt,
    asset_address_: felt,
    market_address_: felt,
    holding_address_: felt,
    trading_fees_address_: felt,
    fees_balance_address_: felt,
    liquidate_address_: felt,
    liquidity_fund_address_: felt,
    insurance_fund_address_: felt,
    max_leverage_: felt,
    min_quantity_: felt,
    maker_direction_: felt,
    trader_stats_list_len_: felt,
    trader_stats_list_: TraderStats*,
    total_order_volume_: felt,
    taker_execution_price: felt,
) -> (trader_stats_list_len: felt, taker_execution_price: felt) {
    alloc_locals;

    local execution_price;
    local margin_amount;
    local borrowed_amount;
    local average_execution_price;
    local trader_stats_list_len;
    local trader_stats_list: TraderStats*;
    local new_total_order_volume;
    local quantity_to_execute;
    local current_quantity_executed;
    local current_order_side;

    // Error messages require local variables to be passed in params
    local current_index;
    current_index = orders_len_ - request_list_len_;

    // Check if the list is empty, if yes return 1
    if (request_list_len_ == 0) {
        return (trader_stats_list_len_, taker_execution_price);
    }

    // Create a struct object for the order
    tempvar temp_order: MultipleOrder = MultipleOrder(
        user_address=[request_list_].user_address,
        sig_r=[request_list_].sig_r,
        sig_s=[request_list_].sig_s,
        liquidator_address=[request_list_].liquidator_address,
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
        close_order=[request_list_].close_order
        );

    // check that the user account is present in account registry (and thus that it was deployed by zkx)
    let (is_registered) = IAccountRegistry.is_registered_user(
        contract_address=account_registry_address_, address_=temp_order.user_address
    );
    with_attr error_message("Trading: User account not registered- {current_index}") {
        assert_not_zero(is_registered);
    }

    // Quantity remaining to be executed
    let (quantity_remaining: felt) = Math64x61_sub(quantity_locked_, quantity_executed_);

    // Taker order
    if (quantity_remaining == 0) {
        // There must only be a single Taker order; hence they must be the last order in the batch
        with_attr error_message(
                "Trading: Taker order must be the last order in the list- {current_index}") {
            assert request_list_len_ = 1;
        }

        // Check for post-only flag; they must always be a maker
        with_attr error_message("Trading: Post Only order cannot be a taker- {current_index}") {
            assert temp_order.post_only = 0;
        }

        // Check for F&K type of orders; they must only be filled completely or rejected
        if (temp_order.time_in_force == FoK) {
            let (diff_check) = Math64x61_sub(temp_order.quantity, quantity_locked_);

            with_attr error_message(
                    "Trading: F&K order should be executed fully- {current_index}") {
                assert diff_check = 0;
                assert temp_order.order_type = LIMIT_ORDER;
            }

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }

        // The matched quanity must be executed for a Taker order
        assert quantity_to_execute = quantity_locked_;

        // The execution price of a taker order is the weighted mean of the Maker orders
        let (new_execution_price: felt) = Math64x61_div(total_order_volume_, quantity_locked_);
        assert execution_price = new_execution_price;

        // Price check
        if (temp_order.order_type == 1) {
            check_within_slippage(
                slippage_=temp_order.slippage,
                price_=temp_order.price,
                execution_price_=new_execution_price,
            );
        } else {
            check_limit_price(
                price_=temp_order.price,
                execution_price_=new_execution_price,
                direction_=temp_order.direction,
            );
        }

        // Reset the variable
        assert current_quantity_executed = 0;

        // Reset the variable
        assert new_total_order_volume = 0;

        // Set the current side as taker
        assert current_order_side = TAKER;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        // Maker Order
    } else {
        with_attr error_message("Trading: Maker orders must be limit orders- {current_index}") {
            assert temp_order.order_type = LIMIT_ORDER;
        }

        if (request_list_len_ == 1) {
            with_attr error_message(
                    "Trading: Maker order cannot be the last order in the list- {current_index}") {
                assert 1 = 0;
            }
        }

        // Get min of remaining quantity and the order quantity
        let cmp_res = is_le(quantity_remaining, temp_order.quantity);

        // If yes, make the quantity_to_execute to be quantity_remaining
        // i.e Partial order
        if (cmp_res == 1) {
            assert quantity_to_execute = quantity_remaining;

            // If no, make quantity_to_execute to be the temp_order.quantity
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
            // Full execution
        } else {
            assert quantity_to_execute = temp_order.quantity;

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }

        // Add the executed quantity to the running sum of quantity executed
        let (current_quantity_executed_felt: felt) = Math64x61_add(
            quantity_executed_, quantity_to_execute
        );
        // Write to local variable
        assert current_quantity_executed = current_quantity_executed_felt;

        // Limit price of the maker is used as the execution price
        assert execution_price = temp_order.price;

        // Add to the weighted sum of the execution prices
        let (new_total_order_volume_) = Math64x61_mul(temp_order.price, quantity_to_execute);
        // Write to local variable
        assert new_total_order_volume = new_total_order_volume_;

        // Set the current side as maker
        assert current_order_side = MAKER;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Price Check
    with_attr error_message("Trading: Execution price not in range- {current_index}") {
        assert_in_range(execution_price, lower_limit_, upper_limit_);
    }

    // If the order is to be opened
    if (temp_order.close_order == 1) {
        let (
            average_execution_price_temp: felt,
            margin_amount_temp: felt,
            borrowed_amount_temp: felt,
            trader_stats_list_len_temp: felt,
        ) = process_open_orders(
            order_=temp_order,
            execution_price_=execution_price,
            order_size_=quantity_to_execute,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            trading_fees_address_=trading_fees_address_,
            liquidity_fund_address_=liquidity_fund_address_,
            liquidate_address_=liquidate_address_,
            fees_balance_address_=fees_balance_address_,
            holding_address_=holding_address_,
            trader_stats_list_len_=trader_stats_list_len_,
            trader_stats_list_=trader_stats_list_,
            current_index_=current_index,
            side_=current_order_side,
        );
        assert margin_amount = margin_amount_temp;
        assert borrowed_amount = borrowed_amount_temp;
        assert average_execution_price = average_execution_price_temp;
        assert trader_stats_list_len = trader_stats_list_len_temp;
        assert trader_stats_list = trader_stats_list_ + TraderStats.SIZE;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        let (
            average_execution_price_temp: felt,
            margin_amount_temp: felt,
            borrowed_amount_temp: felt,
            trader_stats_list_len_temp: felt,
        ) = process_close_orders(
            order_=temp_order,
            execution_price_=execution_price,
            order_size_=quantity_to_execute,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            liquidity_fund_address_=liquidity_fund_address_,
            insurance_fund_address_=insurance_fund_address_,
            holding_address_=holding_address_,
            trader_stats_list_len_=trader_stats_list_len_,
            trader_stats_list_=trader_stats_list_,
            current_index_=current_index,
        );
        assert margin_amount = margin_amount_temp;
        assert borrowed_amount = borrowed_amount_temp;
        assert average_execution_price = average_execution_price_temp;
        assert trader_stats_list_len = trader_stats_list_len_temp;
        assert trader_stats_list = trader_stats_list_ + TraderStats.SIZE;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Create a temporary order object
    let temp_order_request: OrderRequest = OrderRequest(
        order_id=temp_order.order_id,
        market_id=temp_order.market_id,
        direction=temp_order.direction,
        price=temp_order.price,
        quantity=temp_order.quantity,
        leverage=temp_order.leverage,
        slippage=temp_order.slippage,
        order_type=temp_order.order_type,
        time_in_force=temp_order.time_in_force,
        post_only=temp_order.post_only,
        close_order=temp_order.close_order,
        liquidator_address=temp_order.liquidator_address,
    );

    // Create a temporary signature object
    let temp_signature: Signature = Signature(r_value=temp_order.sig_r, s_value=temp_order.sig_s);

    // Call the account contract to initialize the order
    IAccountManager.execute_order(
        contract_address=temp_order.user_address,
        request=temp_order_request,
        signature=temp_signature,
        size=quantity_to_execute,
        execution_price=average_execution_price,
        margin_amount=margin_amount,
        borrowed_amount=borrowed_amount,
        market_id=market_id_,
    );

    trade_execution.emit(
        address=temp_order.user_address,
        request=temp_order_request,
        market_id=market_id_,
        execution_price=average_execution_price,
    );

    // Market Check
    with_attr error_message(
            "Trading: All orders in a batch must be from the same market- {current_index}") {
        assert temp_order.market_id = market_id_;
    }

    // Leverage check minimum
    with_attr error_message("Trading: Leverage must be >= 1- {current_index}") {
        assert_le(LEVERAGE_ONE, temp_order.leverage);
    }

    // If it's the first order in the array
    if (maker_direction_ == 0) {
        // Get the market details
        let (market: Market) = IMarkets.get_market(
            contract_address=market_address_, market_id_=market_id_
        );

        // Tradable check
        with_attr error_message("Trading: Market is not tradable- {current_index}") {
            assert_not_zero(market.is_tradable);
        }

        // Size check
        with_attr error_message(
                "Trading: Quantity must be >= to the minimum order size- {current_index}") {
            assert_le(market.minimum_order_size, temp_order.quantity);
        }

        // Leverage check maximum
        with_attr error_message(
                "Trading: Leverage must be <= to the maximum allowed leverage- {current_index}") {
            assert_le(temp_order.leverage, market.maximum_leverage);
        }

        return check_and_execute(
            quantity_locked_=quantity_locked_,
            market_id_=market_id_,
            collateral_id_=collateral_id_,
            lower_limit_=lower_limit_,
            upper_limit_=upper_limit_,
            orders_len_=orders_len_,
            request_list_len_=request_list_len_ - 1,
            request_list_=request_list_ + MultipleOrder.SIZE,
            quantity_executed_=current_quantity_executed,
            account_registry_address_=account_registry_address_,
            asset_address_=asset_address_,
            market_address_=market_address_,
            holding_address_=holding_address_,
            trading_fees_address_=trading_fees_address_,
            fees_balance_address_=fees_balance_address_,
            liquidate_address_=liquidate_address_,
            liquidity_fund_address_=liquidity_fund_address_,
            insurance_fund_address_=insurance_fund_address_,
            max_leverage_=market.currently_allowed_leverage,
            min_quantity_=market.minimum_order_size,
            maker_direction_=temp_order.direction,
            trader_stats_list_len_=trader_stats_list_len,
            trader_stats_list_=trader_stats_list,
            total_order_volume_=new_total_order_volume,
            taker_execution_price=0,
        );
    }

    // Leverage check maximum
    with_attr error_message(
            "Trading: Leverage must be <= to the maximum allowed leverage- {current_index}") {
        assert_le(temp_order.leverage, max_leverage_);
    }

    // Direction Check
    if (request_list_len_ == 1) {
        tempvar direction_check = maker_direction_ - temp_order.direction;
        with_attr error_message(
                "Trading: Taker order must be in opposite direction of Maker order(s)- {current_index}") {
            assert_not_zero(direction_check);
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        with_attr error_message(
                "Trading: All Maker orders must be in the same direction- {current_index}") {
            assert maker_direction_ = temp_order.direction;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Size Check
    with_attr error_message(
            "Trading: Quantity must be >= to the minimum order size- {current_index}") {
        assert_le(min_quantity_, temp_order.quantity);
    }

    // Recursive Call
    return check_and_execute(
        quantity_locked_=quantity_locked_,
        market_id_=market_id_,
        collateral_id_=collateral_id_,
        lower_limit_=lower_limit_,
        upper_limit_=upper_limit_,
        orders_len_=orders_len_,
        request_list_len_=request_list_len_ - 1,
        request_list_=request_list_ + MultipleOrder.SIZE,
        quantity_executed_=current_quantity_executed,
        account_registry_address_=account_registry_address_,
        asset_address_=asset_address_,
        market_address_=market_address_,
        holding_address_=holding_address_,
        trading_fees_address_=trading_fees_address_,
        fees_balance_address_=fees_balance_address_,
        liquidate_address_=liquidate_address_,
        liquidity_fund_address_=liquidity_fund_address_,
        insurance_fund_address_=insurance_fund_address_,
        max_leverage_=max_leverage_,
        min_quantity_=0,
        maker_direction_=0,
        trader_stats_list_len_=trader_stats_list_len,
        trader_stats_list_=trader_stats_list,
        total_order_volume_=new_total_order_volume,
        taker_execution_price=execution_price,
    );
}
