%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from contracts.libraries.CommonLibrary import CommonLib
from contracts.DataTypes import MultipleOrder, TraderStats

@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    return ();
}

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
    return ();
}
