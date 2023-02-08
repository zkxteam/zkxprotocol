%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import abs_value
from starkware.starknet.common.syscalls import get_caller_address

from contracts.Constants import CLOSE, OPEN, TradingStats_INDEX
from contracts.DataTypes import TraderStats, VolumeMetaData
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.CommonLibrary import CommonLib
from contracts.Math_64x61 import Math64x61_add

// /////////
// Events //
// /////////

// Event emitted when trader's fee collected for a market in a season is recorded
@event
func trader_fee_recorded(season_id: felt, market_id: felt, trader_address: felt, fee_64x61: felt) {
}

// Event emitted when total fee collected by the platform for a market in a season is recorded
@event
func total_fee_recorded(season_id: felt, market_id: felt, total_fee_64x61: felt) {
}

// Event emitted when trader's order volume for a market in a season is recorded
@event
func trader_order_volume_recorded(
    season_id: felt, market_id: felt, trader_address: felt, order_volume_64x61: felt
) {
}

// Event emitted when trader's orders count for a market in a season is recorded
@event
func trader_orders_count_recorded(
    season_id: felt, market_id: felt, trader_address: felt, orders_count: felt
) {
}

// Event emitted when trader's pnl for a market in a season is recorded
@event
func trader_pnl_recorded(season_id: felt, market_id: felt, trader_address: felt, pnl_64x61: felt) {
}

// Event emitted when trader's margin for a market in a season is recorded
@event
func trader_margin_recorded(
    season_id: felt, market_id: felt, trader_address: felt, margin_amount_64x61: felt
) {
}

// //////////
// Storage //
// //////////

// Stores the fee charged on a trader for a market in a season
@storage_var
func trader_fee_by_market(season_id: felt, market_id: felt, trader_address: felt) -> (
    fee_64x61: felt
) {
}

// Stores total fee collected by the platform for a market in a season
@storage_var
func total_fee_by_market(season_id: felt, market_id: felt) -> (total_fee_64x61: felt) {
}

// Stores the total order volume recorded for a volume_type in a season for a trader
@storage_var
func trader_order_volume_by_market(trader_address: felt, volume_type: VolumeMetaData) -> (
    order_volume_64x61: felt
) {
}

// Stores the total number of recorded trades for a volume_type in a season for a trader
@storage_var
func trader_orders_count_by_market(trader_address: felt, volume_type: VolumeMetaData) -> (
    orders_count: felt
) {
}

// Stores the pnl of a trader for a market in a season
@storage_var
func trader_pnl_by_market(season_id: felt, market_id: felt, trader_address: felt) -> (
    pnl_64x61: felt
) {
}

// Stores margin collected while opening a position for a market in a season
@storage_var
func trader_margin_by_market(season_id: felt, market_id: felt, trader_address: felt) -> (
    margin_amount_64x61: felt
) {
}

// //////////////
// Constructor //
// //////////////

// @notice Constructor of the smart-contract
// @param registry_address_ - Address of the AuthorizedRegistry contract
// @param version_ - Version of this contract
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

// @notice View function to get trader's recorded fee
// @param season_id_ - id of the season
// @param market_id_ - id of the market
// @param trader_address_ - l2 address of the trader
// @return fee_64x61 - returns the fee charged on a trader for a market in a season
@view
func get_trader_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, market_id_: felt, trader_address_: felt
) -> (fee_64x61: felt) {
    let (fee_64x61) = trader_fee_by_market.read(season_id_, market_id_, trader_address_);
    return (fee_64x61,);
}

// @notice View function to get the total fee collected by the platform for a market in a season
// @param season_id_ - id of the season
// @param market_id_ - id of the market
// @return total_fee_64x61 - returns total fee collected by the platform for a market in a season
@view
func get_total_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, market_id_: felt
) -> (total_fee_64x61: felt) {
    let (total_fee_64x61) = total_fee_by_market.read(season_id_, market_id_);
    return (total_fee_64x61,);
}

// @notice View function to get trader's order volume for a market in a season
// @param trader_address_ - l2 address of the trader
// @param volume_type_ - contains season_id, market_id and order type
// @return number_of_orders - returns the no.of orders for a market in a season by a trader
// @return total_volume_64x61 - returns the total order volume for a market in a season by a trader
@view
func get_trader_order_volume{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    trader_address_: felt, volume_type_: VolumeMetaData
) -> (number_of_orders: felt, total_volume_64x61: felt) {
    let (current_num_orders) = trader_orders_count_by_market.read(trader_address_, volume_type_);
    let (current_total_volume_64x61) = trader_order_volume_by_market.read(
        trader_address_, volume_type_
    );
    return (current_num_orders, current_total_volume_64x61);
}

// @notice View function to get trader's pnl for a market in a season
// @param season_id_ - id of the season
// @param market_id_ - id of the market
// @param trader_address_ - l2 address of the trader
// @return pnl_64x61 - returns profit or loss on a trader for a market in a season
@view
func get_trader_pnl{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, market_id_: felt, trader_address_: felt
) -> (pnl_64x61: felt) {
    let (pnl_64x61) = trader_pnl_by_market.read(season_id_, market_id_, trader_address_);
    return (pnl_64x61,);
}

// @notice View function to get trader's margin amount for a market in a season
// @param season_id_ - id of the season
// @param market_id_ - id of the market
// @param trader_address_ - l2 address of the trader
// @return margin_amount_64x61 - returns trader'a margin amount for a market in a season
@view
func get_trader_margin_amount{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, market_id_: felt, trader_address_: felt
) -> (margin_amount_64x61: felt) {
    let (margin_amount_64x61) = trader_margin_by_market.read(
        season_id_, market_id_, trader_address_
    );
    return (margin_amount_64x61,);
}

// ///////////
// External //
// ///////////

// @notice This function is used to record trader stats for a market in a season
// @param season_id_ - id of the season
// @param market_id_ - id of the market
// @param trader_stats_list_len - length of the trader fee list
// @param trader_stats_list - List which stores traders fee
@external
func record_trader_stats{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, market_id_: felt, trader_stats_list_len: felt, trader_stats_list: TraderStats*
) {
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (trading_stats_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=TradingStats_INDEX, version=version
    );

    // Check that this call originated from Trading stats contract
    with_attr error_message("UserStats: Stats can be recorded only by TradingStats contract") {
        assert caller = trading_stats_address;
    }

    return update_trader_stats_recurse(
        season_id_, market_id_, 0, 0, trader_stats_list_len, trader_stats_list
    );
}

// ///////////
// Internal //
// ///////////

func update_trader_stats_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    market_id_: felt,
    iterator_: felt,
    current_total_fee_64x61_: felt,
    trader_stats_list_len: felt,
    trader_stats_list: TraderStats*,
) {
    alloc_locals;
    if (iterator_ == trader_stats_list_len) {
        let (current_fee_64x61) = total_fee_by_market.read(season_id_, market_id_);
        let (updated_fee_64x61) = Math64x61_add(current_total_fee_64x61_, current_fee_64x61);
        total_fee_by_market.write(season_id_, market_id_, updated_fee_64x61);

        // Emit event
        total_fee_recorded.emit(season_id_, market_id_, updated_fee_64x61);

        return ();
    }
    let trader_address = [trader_stats_list].trader_address;
    local total_fee_64x61;

    // 1. Update trader fee
    // Fee is charged only for open orders. So, if life_cycle is 1 (open order) we record the fee.
    if ([trader_stats_list].life_cycle == OPEN) {
        let fee_64x61 = [trader_stats_list].fee_64x61;
        let (current_trader_fee_64x61) = trader_fee_by_market.read(
            season_id_, market_id_, trader_address
        );
        let (updated_trader_fee_64x61) = Math64x61_add(current_trader_fee_64x61, fee_64x61);
        let (updated_total_fee_64x61) = Math64x61_add(current_total_fee_64x61_, fee_64x61);
        trader_fee_by_market.write(
            season_id_, market_id_, trader_address, updated_trader_fee_64x61
        );
        assert total_fee_64x61 = updated_total_fee_64x61;

        // Emit event
        trader_fee_recorded.emit(season_id_, market_id_, trader_address, updated_trader_fee_64x61);
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        assert total_fee_64x61 = current_total_fee_64x61_;
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // 2. Update running total of order volume and order count
    // Order volume is recorded for all order types
    let order_volume_64x61 = [trader_stats_list].order_volume_64x61;
    let volume_metadata: VolumeMetaData = VolumeMetaData(
        season_id=season_id_, market_id=market_id_, life_cycle=[trader_stats_list].life_cycle
    );

    let (current_order_volume_64x61) = trader_order_volume_by_market.read(
        trader_address, volume_metadata
    );
    let (updated_order_volume_64x61) = Math64x61_add(
        current_order_volume_64x61, order_volume_64x61
    );
    trader_order_volume_by_market.write(
        trader_address, volume_metadata, updated_order_volume_64x61
    );

    // Emit event
    trader_order_volume_recorded.emit(
        season_id_, market_id_, trader_address, updated_order_volume_64x61
    );

    let (current_orders_count) = trader_orders_count_by_market.read(
        trader_address, volume_metadata
    );
    trader_orders_count_by_market.write(trader_address, volume_metadata, current_orders_count + 1);

    // Emit event
    trader_orders_count_recorded.emit(
        season_id_, market_id_, trader_address, current_orders_count + 1
    );

    // 3. Update PnL
    // Realized PnL is calculated when trader closes a position. So, we record PnL for close orders.
    if ([trader_stats_list].life_cycle == CLOSE) {
        let pnl_64x61 = [trader_stats_list].pnl_64x61;
        let abs_pnl_64x61 = abs_value(pnl_64x61);
        let (current_pnl_64x61) = trader_pnl_by_market.read(season_id_, market_id_, trader_address);
        let (updated_pnl_64x61) = Math64x61_add(current_pnl_64x61, abs_pnl_64x61);
        trader_pnl_by_market.write(season_id_, market_id_, trader_address, updated_pnl_64x61);

        // Emit event
        trader_pnl_recorded.emit(season_id_, market_id_, trader_address, updated_pnl_64x61);

        let margin_amount_64x61 = [trader_stats_list].margin_amount_64x61;
        let (current_margin_amount_64x61) = trader_margin_by_market.read(
            season_id_, market_id_, trader_address
        );
        let (updated_margin_amount_64x61) = Math64x61_add(
            current_margin_amount_64x61, margin_amount_64x61
        );
        trader_margin_by_market.write(
            season_id_, market_id_, trader_address, updated_margin_amount_64x61
        );

        // Emit event
        trader_margin_recorded.emit(
            season_id_, market_id_, trader_address, updated_margin_amount_64x61
        );

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    return update_trader_stats_recurse(
        season_id_,
        market_id_,
        iterator_ + 1,
        total_fee_64x61,
        trader_stats_list_len,
        trader_stats_list + TraderStats.SIZE,
    );
}
