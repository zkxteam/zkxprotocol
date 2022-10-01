%lang starknet

from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math import assert_in_range, assert_le, assert_not_zero
from starkware.cairo.common.math import abs_value
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.common.syscalls import get_block_timestamp

from contracts.Constants import (
    AccountRegistry_INDEX,
    AdminAuth_INDEX,
    Asset_INDEX,
    DELEVERAGING_ORDER,
    FeeBalance_INDEX,
    Holding_INDEX,
    InsuranceFund_INDEX,
    LIMIT_ORDER,
    Liquidate_INDEX,
    LIQUIDATION_ORDER,
    LiquidityFund_INDEX,
    LONG,
    Market_INDEX,
    MARKET_ORDER,
    MarketPrices_INDEX,
    SHORT,
    STOP_ORDER,
    TradingFees_INDEX,
    TradingStats_INDEX,
)
from contracts.DataTypes import (
    Asset,
    Market,
    MarketPrice,
    MultipleOrder,
    PositionDetails,
    OrderRequest,
    Signature,
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
from contracts.Math_64x61 import Math64x61_mul, Math64x61_div, Math64x61_ONE

//############
// Constants #
//############
const TWO_PERCENT = 46116860184273879;

//#########
// Events #
//#########

// Event emitted whenever a new market is added
@event
func trade_execution(address: felt, request: OrderRequest, market_id: felt, execution_price: felt) {
}

//##############
// Constructor #
//##############

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

//#####################
// External Functions #
//#####################

// @notice Function to execute multiple orders in a batch
// @param size_ - Size of the order to be executed
// @param execution_price_ - Price at which the orders must be executed
// @param request_list_len - No of orders in the batch
// @param request_list - The batch of the orders
@external
func execute_batch{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*
}(
    size_: felt,
    execution_price_: felt,
    marketID_: felt,
    request_list_len: felt,
    request_list: MultipleOrder*,
) -> () {
    alloc_locals;

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Calculate the timestamp
    let (current_timestamp) = get_block_timestamp();

    // Get market contract address
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get Market from the corresponding Id
    let (market: Market) = IMarkets.get_market(contract_address=market_address, id=marketID_);

    tempvar ttl = market.ttl;

    // Get market prices contract address
    let (market_prices_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=MarketPrices_INDEX, version=version
    );

    // Get Market price for the corresponding market Id
    let (market_prices: MarketPrice) = IMarketPrices.get_market_price(
        contract_address=market_prices_contract_address, id=marketID_
    );

    tempvar timestamp = market_prices.timestamp;
    tempvar time_difference = current_timestamp - timestamp;
    let status = is_le(time_difference, ttl);

    // update market price
    if (status == FALSE) {
        IMarketPrices.update_market_price(
            contract_address=market_prices_contract_address, id=marketID_, price=execution_price_
        );
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
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
    ) = get_registry_addresses();

    // Recursively loop through the orders in the batch
    let (result) = check_and_execute(
        size_,
        0,
        0,
        marketID_,
        execution_price_,
        request_list_len,
        request_list,
        0,
        account_registry_address,
        asset_address,
        market_address,
        holding_address,
        trading_fees_address,
        fees_balance_address,
        liquidate_address,
        liquidity_fund_address,
        insurance_fund_address,
        0,
    );

    // Check if every order has a counter order
    with_attr error_message("check and execute returned non zero integer.") {
        assert result = 0;
    }

    ITradingStats.record_trade_batch_stats(
        contract_address=trading_stats_address,
        pair_id_=marketID_,
        order_size_=size_,
        execution_price_=execution_price_,
        request_list_len=request_list_len,
        request_list=request_list,
    );
    return ();
}

//#####################
// Internal Functions #
//#####################

// @notice Internal function to retrieve contract addresses from the Auth Registry
// @returns account_registry_address - Address of the Account Registry contract
// @returns asset_address - Address of the Asset contract
// @returns holding_address - Address of the Holding contract
// @returns trading_fees_address - Address of the Trading contract
// @returns fees_balance_address - Address of the Fee Balance contract
// @returns liquidate_address - Address of the Liquidate contract
// @returns liquidity_fund_address - Address of the Liquidity Fund contract
// @returns insurance_fund_address - Address of the Insurance Fund contract
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
    );
}

// Internal Function to check if the price is fair for an order
// @param order_ - Order to check
// @param execution_price_ - Price at which the order got matched
func check_order_price{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_: MultipleOrder, execution_price_: felt
) {
    // Check if the execution_price is correct
    if (order_.orderType == STOP_ORDER) {
        // if stop order
        if (order_.direction == LONG) {
            // if long stop order
            // check that stop_price <= execution_price <= limit_price
            with_attr error_message(
                    "Stop price should be less than or equal to the execution price for long orders") {
                assert_le(order_.stopPrice, execution_price_);
            }
            tempvar range_check_ptr = range_check_ptr;

            with_attr error_message(
                    "Execution price should be less than or equal to the order price for long orders") {
                assert_le(execution_price_, order_.price);
            }
            tempvar range_check_ptr = range_check_ptr;
        } else {
            // if short stop order
            // check that limit_price <= execution_price <= stop_price
            with_attr error_message(
                    "Order price should be less than or equal to the execution price for short orders") {
                assert_le(order_.price, execution_price_);
            }
            tempvar range_check_ptr = range_check_ptr;

            with_attr error_message(
                    "Execution price should be less than or equal to the stop price for short orders") {
                assert_le(execution_price_, order_.stopPrice);
            }
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar range_check_ptr = range_check_ptr;
    }

    if (order_.orderType == LIMIT_ORDER) {
        // if it's a limit order
        if (order_.direction == LONG) {
            // if it's a long order
            with_attr error_message(
                    "limit-long order execution price should be less than limit price.") {
                assert_le(execution_price_, order_.price);
            }
            tempvar range_check_ptr = range_check_ptr;
        } else {
            // if it's a short order
            with_attr error_message(
                    "limit-short order limit price should be less than execution price.") {
                assert_le(order_.price, execution_price_);
            }
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar range_check_ptr = range_check_ptr;
    }

    if (order_.orderType == MARKET_ORDER) {
        // if it's a market order
        // Calculate 2% of the order price
        let (two_percent) = Math64x61_mul(order_.price, TWO_PERCENT);
        if (order_.direction == LONG) {
            // if it's a long order
            tempvar upperLimit = order_.price + two_percent;

            with_attr error_message("Execution price is 2% above the user defined price") {
                assert_le(execution_price_, upperLimit);
            }
        } else {
            // if it's a short order
            tempvar lowerLimit = order_.price - two_percent;

            with_attr error_message("Execution price is 2% below the user defined price") {
                assert_le(lowerLimit, execution_price_);
            }
        }
        tempvar range_check_ptr = range_check_ptr;
    }

    return ();
}

// @notice Intenal function that processes open orders
// @param order_ - Order request
// @param execution_price_ - The price at which it got matched
// @param order_size_ - The size of the asset that got matched
// @param market_id_ - The market ID of the batch
// @param trading_fees_address_ - Address of the Trading Fees contract
// @param liquidity_fund_address_ - Address of the Liquidity contract
// @param liquidate_address_ - Address of the Liquidate contract
// @param fees_balance_address_ - Address of the Fee Balance contract
// @param holding_address_ - Address of the Holding contract
// @returns average_execution_price_open - Average Execution Price for the order
// @returns margin_amount_open - Margin amount for the order
// @returns borrowed_amount_open - Borrowed amount for the order
func process_open_orders{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_: MultipleOrder,
    execution_price_: felt,
    order_size_: felt,
    market_id_: felt,
    trading_fees_address_: felt,
    liquidity_fund_address_: felt,
    liquidate_address_: felt,
    fees_balance_address_: felt,
    holding_address_: felt,
) -> (average_execution_price_open: felt, margin_amount_open: felt, borrowed_amount_open: felt) {
    alloc_locals;

    local margin_amount_open;
    local borrowed_amount_open;
    local average_execution_price_open;

    // Get the fees from Trading Fee contract
    let (fees_rate) = ITradingFees.get_user_fee_and_discount(
        contract_address=trading_fees_address_, address_=order_.pub_key, side_=order_.side
    );

    // Get order details
    let (position_details: PositionDetails) = IAccountManager.get_position_data(
        contract_address=order_.pub_key, market_id_=market_id_, direction_=order_.direction
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
        let cumulative_order_value = portion_executed_value + current_order_value;
        let cumulative_order_size = position_details.position_size + order_size_;
        let (price) = Math64x61_div(cumulative_order_value, cumulative_order_size);

        assert average_execution_price_open = execution_price_;
        tempvar range_check_ptr = range_check_ptr;
    }

    let (leveraged_position_value) = Math64x61_mul(order_size_, execution_price_);
    let (total_position_value) = Math64x61_div(leveraged_position_value, order_.leverage);
    tempvar amount_to_be_borrowed = leveraged_position_value - total_position_value;

    // Calculate borrowed and margin amounts to be stored in account contract
    margin_amount_open = margin_amount + total_position_value;
    borrowed_amount_open = borrowed_amount + amount_to_be_borrowed;

    let (user_balance) = IAccountManager.get_balance(
        contract_address=order_.pub_key, assetID_=order_.collateralID
    );

    // Calculate the fees for the order
    let (fees) = Math64x61_mul(fees_rate, leveraged_position_value);

    // Calculate the total amount by adding fees
    tempvar total_amount = total_position_value + fees;

    // User must be able to pay the amount
    with_attr error_message(
            "User balance is less than value of the position in trading contract.") {
        assert_le(total_amount, user_balance);
    }

    // Check if the position can be opened
    ILiquidate.check_order_can_be_opened(
        contract_address=liquidate_address_,
        order=order_,
        size=order_size_,
        execution_price=execution_price_,
    );

    // Deduct the amount from account contract
    IAccountManager.transfer_from(
        contract_address=order_.pub_key, assetID_=order_.collateralID, amount=total_amount
    );

    // Update the fees to be paid by user in fee balance contract
    IFeeBalance.update_fee_mapping(
        contract_address=fees_balance_address_,
        address=order_.pub_key,
        assetID_=order_.collateralID,
        fee_to_add=fees,
    );

    // Deduct the amount from liquidity funds if order is leveraged
    let is_non_leveraged = is_le(order_.leverage, Math64x61_ONE);

    if (is_non_leveraged == FALSE) {
        ILiquidityFund.withdraw(
            contract_address=liquidity_fund_address_,
            asset_id_=order_.collateralID,
            amount=amount_to_be_borrowed,
            position_id_=order_.orderID,
        );
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }
    tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;

    // Deposit the funds taken from the user and liquidity fund
    IHolding.deposit(
        contract_address=holding_address_,
        asset_id_=order_.collateralID,
        amount=leveraged_position_value,
    );

    return (average_execution_price_open, margin_amount_open, borrowed_amount_open);
}

// @notice Intenal function that processes close orders including Liquidation & Deleveraging
// @param order_ - Order request
// @param execution_price_ - The price at which it got matched
// @param order_size_ - The size of the asset that got matched
// @param market_id_ - The market ID of the batch
// @param liquidity_fund_address_ - Address of the Liquidity contract
// @param liquidate_address_ - Address of the Liquidate contract
// @param insurance_fund_address - Address of the Insurance Fund contract
// @param holding_address_ - Address of the Holding contract
// @returns average_execution_price_open - Average Execution Price for the order
// @returns margin_amount_open - Margin amount for the order
// @returns borrowed_amount_open - Borrowed amount for the order
func process_close_orders{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_: MultipleOrder,
    execution_price_: felt,
    order_size_: felt,
    market_id_: felt,
    liquidity_fund_address_: felt,
    insurance_fund_address_: felt,
    holding_address_: felt,
) -> (margin_amount_close: felt, borrowed_amount_close: felt, average_execution_price_close: felt) {
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
        contract_address=order_.pub_key, market_id_=market_id_, direction_=parent_direction
    );

    with_attr error_message("The parentPosition size cannot be 0") {
        assert_not_zero(parent_position.position_size);
    }

    let margin_amount = parent_position.margin_amount;
    let borrowed_amount = parent_position.borrowed_amount;
    average_execution_price_close = parent_position.avg_execution_price;

    local diff;
    local actual_execution_price;
    local net_acc_value;

    // current order is short order
    if (order_.direction == SHORT) {
        // Open order was a long order
        actual_execution_price = execution_price_;
        diff = execution_price_ - parent_position.avg_execution_price;
    } else {
        // Open order was a short order
        diff = parent_position.avg_execution_price - execution_price_;
        actual_execution_price = parent_position.avg_execution_price + diff;
    }

    // Calculate pnl and net account value
    let (pnl) = Math64x61_mul(parent_position.position_size, diff);
    net_acc_value = margin_amount + pnl;

    // Total value of the asset at current price
    let (leveraged_amount_out) = Math64x61_mul(order_size_, actual_execution_price);

    // Calculate the amount that needs to be returned to liquidity fund
    let (percent_of_order) = Math64x61_div(order_size_, parent_position.position_size);
    let (value_to_be_returned) = Math64x61_mul(borrowed_amount, percent_of_order);
    let (margin_to_be_reduced) = Math64x61_mul(margin_amount, percent_of_order);

    // Calculate new values for margin and borrowed amounts
    if (order_.orderType == DELEVERAGING_ORDER) {
        borrowed_amount_close = borrowed_amount - leveraged_amount_out;
        margin_amount_close = margin_amount;
    } else {
        borrowed_amount_close = borrowed_amount - value_to_be_returned;
        margin_amount_close = margin_amount - margin_to_be_reduced;
    }

    // Check if the position is to be liquidated
    let not_liquidation = is_le(order_.orderType, 2);

    // If it's just a close order
    if (not_liquidation == TRUE) {
        // Deduct funds from holding contract
        IHolding.withdraw(
            contract_address=holding_address_,
            asset_id_=order_.collateralID,
            amount=leveraged_amount_out,
        );

        // If no leverage is used
        if (order_.leverage == Math64x61_ONE) {
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            ILiquidityFund.deposit(
                contract_address=liquidity_fund_address_,
                asset_id_=order_.collateralID,
                amount=value_to_be_returned,
                position_id_=order_.orderID,
            );
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        // Check if the position is underwater
        let is_loss = is_le(net_acc_value, 0);

        if (is_loss == TRUE) {
            // If yes, deduct the difference from user's balance, can go negative
            IAccountManager.transfer_from(
                contract_address=order_.pub_key,
                assetID_=order_.collateralID,
                amount=leveraged_amount_out - value_to_be_returned,
            );
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            // If not, transfer the remaining to user
            IAccountManager.transfer(
                contract_address=order_.pub_key,
                assetID_=order_.collateralID,
                amount=leveraged_amount_out - value_to_be_returned,
            );
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
    } else {
        // Liquidation order
        if (order_.orderType == LIQUIDATION_ORDER) {
            // Withdraw the position from holding fund
            IHolding.withdraw(
                contract_address=holding_address_,
                asset_id_=order_.collateralID,
                amount=leveraged_amount_out,
            );

            // Return the borrowed fund to the Liquidity fund
            ILiquidityFund.deposit(
                contract_address=liquidity_fund_address_,
                asset_id_=order_.collateralID,
                amount=value_to_be_returned,
                position_id_=order_.orderID,
            );

            // Check if the account value for the position is negative
            let is_negative = is_le(net_acc_value, 0);

            if (is_negative == TRUE) {
                // Absolute value of the acc value
                let deficit = abs_value(net_acc_value);

                // Get the user balance
                let (user_balance) = IAccountManager.get_balance(
                    contract_address=order_.pub_key, assetID_=order_.collateralID
                );

                // Check if the user's balance can cover the deficit
                let is_payable = is_le(deficit, user_balance);

                if (is_payable == TRUE) {
                    // Transfer the full amount from the user
                    IAccountManager.transfer_from(
                        contract_address=order_.pub_key,
                        assetID_=order_.collateralID,
                        amount=deficit,
                    );

                    tempvar syscall_ptr = syscall_ptr;
                    tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                    tempvar range_check_ptr = range_check_ptr;
                } else {
                    // Transfer the partial amount from the user
                    IAccountManager.transfer_from(
                        contract_address=order_.pub_key,
                        assetID_=order_.collateralID,
                        amount=user_balance,
                    );

                    // Transfer the remaining amount from Insurance Fund
                    IInsuranceFund.withdraw(
                        contract_address=insurance_fund_address_,
                        asset_id_=order_.collateralID,
                        amount=deficit - user_balance,
                        position_id_=order_.orderID,
                    );

                    tempvar syscall_ptr = syscall_ptr;
                    tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                    tempvar range_check_ptr = range_check_ptr;
                }
            } else {
                // Deposit the user's remaining margin in Insurance Fund
                IInsuranceFund.deposit(
                    contract_address=insurance_fund_address_,
                    asset_id_=order_.collateralID,
                    amount=net_acc_value,
                    position_id_=order_.orderID,
                );

                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }
        } else {
            // Deleveraging order
            with_attr error_message("Wrong order type passed") {
                assert order_.orderType = DELEVERAGING_ORDER;
            }

            // Withdraw the position from holding fund
            IHolding.withdraw(
                contract_address=holding_address_,
                asset_id_=order_.collateralID,
                amount=leveraged_amount_out,
            );
            // Return the borrowed fund to the Liquidity fund
            ILiquidityFund.deposit(
                contract_address=liquidity_fund_address_,
                asset_id_=order_.collateralID,
                amount=leveraged_amount_out,
                position_id_=order_.orderID,
            );

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    return (average_execution_price_close, margin_amount_close, borrowed_amount_close);
}

// @notice Internal function called by execute_batch
// @param size_ - Size of the order to be executed
// @param assetID_ - Asset ID of the batch to be set by the first order
// @param collateralID_ - Collateral ID of the batch to be set by the first order
// @param marketID_ - Market ID of the batch to be set by the first order
// @param ticker_ - The ticker of each order in the batch
// @param execution_price_ - Price at which the orders must be executed
// @param request_list_len_ - No of orders in the batch
// @param request_list_ - The batch of the orders
// @param sum_ - Net sum of all the orders in the batch
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
func check_and_execute{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    size_: felt,
    assetID_: felt,
    collateralID_: felt,
    marketID_: felt,
    execution_price_: felt,
    request_list_len_: felt,
    request_list_: MultipleOrder*,
    sum: felt,
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
) -> (res: felt) {
    alloc_locals;

    // Check if the list is empty, if yes return 1
    if (request_list_len_ == 0) {
        return (sum,);
    }

    // Create a struct object for the order
    tempvar temp_order: MultipleOrder = MultipleOrder(
        pub_key=[request_list_].pub_key,
        sig_r=[request_list_].sig_r,
        sig_s=[request_list_].sig_s,
        orderID=[request_list_].orderID,
        assetID=[request_list_].assetID,
        collateralID=[request_list_].collateralID,
        price=[request_list_].price,
        stopPrice=[request_list_].stopPrice,
        orderType=[request_list_].orderType,
        positionSize=[request_list_].positionSize,
        direction=[request_list_].direction,
        closeOrder=[request_list_].closeOrder,
        leverage=[request_list_].leverage,
        liquidatorAddress=[request_list_].liquidatorAddress,
        side=[request_list_].side
        );

    // check that the user account is present in account registry (and thus that it was deployed by zkx)
    let (is_registered) = IAccountRegistry.is_registered_user(
        contract_address=account_registry_address_, address_=temp_order.pub_key
    );

    with_attr error_message("User account not registered") {
        assert_not_zero(is_registered);
    }

    // Check if the price is fair
    check_order_price(order_=temp_order, execution_price_=execution_price_);

    // Check if size is less than or equal to postionSize
    let cmp_res = is_le(size_, temp_order.positionSize);

    local order_size;

    if (cmp_res == 1) {
        // If yes, make the order_size to be size
        assert order_size = size_;
    } else {
        // If no, make order_size to be the positionSize̦
        assert order_size = temp_order.positionSize;
    }

    local sum_temp;

    if (temp_order.direction == LONG) {
        assert sum_temp = sum + order_size;
    } else {
        assert sum_temp = sum - order_size;
    }

    local margin_amount;
    local borrowed_amount;
    local average_execution_price;

    // If the order is to be opened
    if (temp_order.closeOrder == FALSE) {
        let (
            average_execution_price_temp: felt, margin_amount_temp: felt, borrowed_amount_temp: felt
        ) = process_open_orders(
            order_=temp_order,
            execution_price_=execution_price_,
            order_size_=order_size,
            market_id_=marketID_,
            trading_fees_address_=trading_fees_address_,
            liquidity_fund_address_=liquidity_fund_address_,
            liquidate_address_=liquidate_address_,
            fees_balance_address_=fees_balance_address_,
            holding_address_=holding_address_,
        );
        assert margin_amount = margin_amount_temp;
        assert borrowed_amount = borrowed_amount_temp;
        assert average_execution_price = average_execution_price_temp;
    } else {
        let (
            average_execution_price_temp: felt, margin_amount_temp: felt, borrowed_amount_temp: felt
        ) = process_close_orders(
            order_=temp_order,
            execution_price_=execution_price_,
            order_size_=order_size,
            market_id_=marketID_,
            liquidity_fund_address_=liquidity_fund_address_,
            insurance_fund_address_=insurance_fund_address_,
            holding_address_=holding_address_,
        );
        assert margin_amount = margin_amount_temp;
        assert borrowed_amount = borrowed_amount_temp;
        assert average_execution_price = average_execution_price_temp;
    }

    // Create a temporary order object
    let temp_order_request: OrderRequest = OrderRequest(
        orderID=temp_order.orderID,
        assetID=temp_order.assetID,
        collateralID=temp_order.collateralID,
        price=temp_order.price,
        stopPrice=temp_order.stopPrice,
        orderType=temp_order.orderType,
        positionSize=temp_order.positionSize,
        direction=temp_order.direction,
        closeOrder=temp_order.closeOrder,
        leverage=temp_order.leverage,
        liquidatorAddress=temp_order.liquidatorAddress,
    );

    // Create a temporary signature object
    let temp_signature: Signature = Signature(r_value=temp_order.sig_r, s_value=temp_order.sig_s);

    // Call the account contract to initialize the order
    IAccountManager.execute_order(
        contract_address=temp_order.pub_key,
        request=temp_order_request,
        signature=temp_signature,
        size=order_size,
        execution_price=average_execution_price,
        margin_amount=margin_amount,
        borrowed_amount=borrowed_amount,
        market_id=marketID_,
    );

    trade_execution.emit(
        address=temp_order.pub_key,
        request=temp_order_request,
        market_id=marketID_,
        execution_price=average_execution_price,
    );

    // If it's the first order in the array
    if (assetID_ == 0) {
        // Check if the asset is tradable
        let (asset: Asset) = IAsset.get_asset(
            contract_address=asset_address_, id=temp_order.assetID
        );
        let (collateral: Asset) = IAsset.get_asset(
            contract_address=asset_address_, id=temp_order.collateralID
        );
        let (market: Market) = IMarkets.get_market(contract_address=market_address_, id=marketID_);

        with_attr error_message("asset is non tradable in trading contract.") {
            assert_not_zero(asset.tradable);
        }

        with_attr error_message("asset is non collaterable in trading contract.") {
            assert_not_zero(collateral.collateral);
        }

        with_attr error_message("market is non tradable in trading contract.") {
            assert_not_zero(market.is_tradable);
        }

        with_attr error_message("Trading: too high leverage") {
            assert_le(temp_order.leverage, market.currently_allowed_leverage);
        }

        // Recursive call with the ticker and price to compare against
        return check_and_execute(
            size_,
            temp_order.assetID,
            temp_order.collateralID,
            marketID_,
            execution_price_,
            request_list_len_ - 1,
            request_list_ + MultipleOrder.SIZE,
            sum_temp,
            account_registry_address_,
            asset_address_,
            market_address_,
            holding_address_,
            trading_fees_address_,
            fees_balance_address_,
            liquidate_address_,
            liquidity_fund_address_,
            insurance_fund_address_,
            market.currently_allowed_leverage,
        );
    }

    // Assert that the order has the same ticker and price as the first order
    with_attr error_message(
            "assetID is not same as opposite order's assetID in trading contract.") {
        assert assetID_ = temp_order.assetID;
    }

    with_attr error_message(
            "collateralID is not same as opposite order's collateralID in trading contract.") {
        assert collateralID_ = temp_order.collateralID;
    }

    with_attr error_message("leverage is not less than currently allowed leverage of the asset") {
        assert_le(temp_order.leverage, max_leverage_);
    }

    // Recursive Call
    return check_and_execute(
        size_,
        assetID_,
        collateralID_,
        marketID_,
        execution_price_,
        request_list_len_ - 1,
        request_list_ + MultipleOrder.SIZE,
        sum_temp,
        account_registry_address_,
        asset_address_,
        market_address_,
        holding_address_,
        trading_fees_address_,
        fees_balance_address_,
        liquidate_address_,
        liquidity_fund_address_,
        insurance_fund_address_,
        max_leverage_,
    );
}
