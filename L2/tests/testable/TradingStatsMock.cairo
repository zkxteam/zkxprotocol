%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from contracts.libraries.CommonLibrary import CommonLib
from contracts.DataTypes import MultipleOrder, TraderStats
from contracts.Math_64x61 import Math64x61_add

// //////////
// Storage //
// //////////

// stores current open interest corresponding to a market
@storage_var
func open_interest(market_id: felt) -> (res: felt) {
}

// //////////////
// Constructor //
// //////////////

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

// @dev - This function returns open interest corresponding to a specific market
@view
func get_open_interest{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_
) -> (res: felt) {
    let (current_open_interest) = open_interest.read(market_id_);
    return (current_open_interest,);
}

// ///////////
// External //
// ///////////

@external
func record_trade_batch_stats{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt,
    execution_price_64x61_: felt,
    request_list_len: felt,
    request_list: MultipleOrder*,
    trader_stats_list_len: felt,
    trader_stats_list: TraderStats*,
    executed_sizes_list_len: felt,
    executed_sizes_list: felt*,
    open_interest_: felt,
) {
    let (current_open_interest) = open_interest.read(market_id_);
    let (new_open_interest) = Math64x61_add(current_open_interest, open_interest_);
    open_interest.write(market_id_, new_open_interest);
    return ();
}
