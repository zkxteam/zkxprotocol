%lang starknet

from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address

from contracts.Constants import Hightide_INDEX, TradingStats_INDEX
from contracts.DataTypes import TraderStats, TradingSeason
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHighTide import IHighTide
from contracts.libraries.CommonLibrary import CommonLib
from contracts.Math_64x61 import Math64x61_add

// /////////
// Events //
// /////////

// Event emitted when trader's fee collected for a pair in a season is recorded
@event
func trader_fee_recorded(
    caller: felt, season_id: felt, pair_id: felt, trader_address: felt, fee_64x61: felt
) {
}

// Event emitted when total fee collected by the platform for a pair in a season is recorded
@event
func total_fee_recorded(caller: felt, season_id: felt, pair_id: felt, total_fee_64x61: felt) {
}

// Event emitted when trader's open order value for a pair in a season is recorded
@event
func trader_open_order_value_recorded(
    caller: felt, season_id: felt, pair_id: felt, trader_address: felt, open_order_value_64x61: felt
) {
}

// Event emitted when trader's open orders count for a pair in a season is recorded
@event
func trader_open_orders_count_recorded(
    caller: felt, season_id: felt, pair_id: felt, trader_address: felt, open_orders_count: felt
) {
}

// //////////
// Storage //
// //////////

// Stores the fee charged on a trader for a pair in a season
@storage_var
func trader_fee_by_market(season_id: felt, pair_id: felt, trader_address: felt) -> (
    fee_64x61: felt
) {
}

// Stores total fee collected by the platform for a pair in a season
@storage_var
func total_fee_by_market(season_id: felt, pair_id: felt) -> (total_fee_64x61: felt) {
}

// Stores the open order value of a trader for a pair in a season
@storage_var
func trader_open_order_value_by_market(season_id: felt, pair_id: felt, trader_address: felt) -> (
    open_order_value_64x61: felt
) {
}

// Stores the open orders count of a trader for a pair in a season
@storage_var
func trader_open_orders_count_by_market(season_id: felt, pair_id: felt, trader_address: felt) -> (
    open_orders_count: felt
) {
}

// //////////////
// Constructor //
// //////////////

// @notice Constructor of the smart-contract
// @param registry_address - Address of the AuthorizedRegistry contract
// @param version - Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address: felt, version: felt
) {
    CommonLib.initialize(registry_address, version);
    return ();
}

// ///////
// View //
// ///////

// @notice View function to get current season id
// @param season_id - id of the season
// @param pair_id - id of the pair
// @param trader_address - l2 address of the trader
// @return fee_64x61 - returns the fee charged on a trader for a pair in a season
@view
func get_trader_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt, pair_id: felt, trader_address: felt
) -> (fee_64x61: felt) {
    let (fee_64x61) = trader_fee_by_market.read(season_id, pair_id, trader_address);
    return (fee_64x61,);
}

// @notice View function to get the total fee collected by the platform for a pair in a season
// @param season_id - id of the season
// @param pair_id - id of the pair
// @return total_fee_64x61 - returns total fee collected by the platform for a pair in a season
@view
func get_total_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt, pair_id: felt
) -> (total_fee_64x61: felt) {
    let (total_fee_64x61) = total_fee_by_market.read(season_id, pair_id);
    return (total_fee_64x61,);
}

// ///////////
// External //
// ///////////

// @notice This function is used to record trader stats for a pair in a season
// @param season_id - id of the season
// @param pair_id - id of the pair
// @param trader_stats_list_len - length of the trader fee list
// @param trader_stats_list - List which stores traders fee
@external
func record_trader_stats{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt, pair_id: felt, trader_stats_list_len: felt, trader_stats_list: TraderStats*
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
        season_id, pair_id, 0, 0, trader_stats_list_len, trader_stats_list
    );
}

// ///////////
// Internal //
// ///////////

func update_trader_stats_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt,
    pair_id: felt,
    iterator: felt,
    current_total_fee_64x61: felt,
    trader_stats_list_len: felt,
    trader_stats_list: TraderStats*,
) {
    let (caller) = get_caller_address();
    if (iterator == trader_stats_list_len) {
        let (current_fee_64x61) = total_fee_by_market.read(season_id, pair_id);
        let (updated_fee_64x61) = Math64x61_add(current_total_fee_64x61, current_fee_64x61);
        total_fee_by_market.write(season_id, pair_id, updated_fee_64x61);

        // Emit event
        total_fee_recorded.emit(caller, season_id, pair_id, updated_fee_64x61);

        return ();
    }
    let trader_address = [trader_stats_list].trader_address;

    // 1. Increment trader fee
    let fee_64x61 = [trader_stats_list].fee_64x61;
    let (current_trader_fee_64x61) = trader_fee_by_market.read(season_id, pair_id, trader_address);
    let (updated_trader_fee_64x61) = Math64x61_add(current_trader_fee_64x61, fee_64x61);
    let (updated_total_fee_64x61) = Math64x61_add(current_total_fee_64x61, fee_64x61);
    trader_fee_by_market.write(season_id, pair_id, trader_address, updated_trader_fee_64x61);

    // Emit event
    trader_fee_recorded.emit(caller, season_id, pair_id, trader_address, updated_trader_fee_64x61);

    // 2. Increment trader open order value
    let open_order_value_64x61 = [trader_stats_list].open_order_value_64x61;
    let (current_order_value_64x61) = trader_open_order_value_by_market.read(
        season_id, pair_id, trader_address
    );
    let (updated_order_value_64x61) = Math64x61_add(
        current_order_value_64x61, open_order_value_64x61
    );
    trader_open_order_value_by_market.write(
        season_id, pair_id, trader_address, updated_order_value_64x61
    );

    // Emit event
    trader_open_order_value_recorded.emit(
        caller, season_id, pair_id, trader_address, updated_order_value_64x61
    );

    // 3. Increment traders open order count
    let open_orders_count = [trader_stats_list].open_orders_count;
    let (current_open_orders_count) = trader_open_orders_count_by_market.read(
        season_id, pair_id, trader_address
    );
    let (updated_open_orders_count) = Math64x61_add(current_open_orders_count, open_orders_count);
    trader_open_orders_count_by_market.write(
        season_id, pair_id, trader_address, updated_open_orders_count
    );

    // Emit event
    trader_open_orders_count_recorded.emit(
        caller, season_id, pair_id, trader_address, updated_open_orders_count
    );

    return update_trader_stats_recurse(
        season_id,
        pair_id,
        iterator + 1,
        updated_total_fee_64x61,
        trader_stats_list_len,
        trader_stats_list + TraderStats.SIZE,
    );
}
