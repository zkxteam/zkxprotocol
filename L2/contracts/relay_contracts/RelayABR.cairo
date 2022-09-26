%lang starknet

from contracts.interfaces.IABR import IABR
from contracts.libraries.RelayLibrary import record_call_details, get_inner_contract, initialize

from starkware.cairo.common.cairo_builtins import HashBuiltin

// @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt, index_: felt
) {
    initialize(registry_address_, version_, index_);
    return ();
}

// @notice - All the following are mirror functions for ABR.cairo - just record call details and forward call

@external
func calculate_abr{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id: felt, perp_index_len: felt, perp_index: felt*, perp_mark_len: felt, perp_mark: felt*
) -> (res: felt) {
    alloc_locals;
    record_call_details('calculate_abr');
    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    let (inner_address) = get_inner_contract();
    let (res) = IABR.calculate_abr(
        inner_address, market_id, perp_index_len, perp_index, perp_mark_len, perp_mark
    );

    return (res,);
}

@view
func get_abr_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id: felt
) -> (abr: felt, price: felt, timestamp: felt) {
    let (inner_address) = get_inner_contract();
    let (abr, price, timestamp) = IABR.get_abr_value(inner_address, market_id);
    return (abr, price, timestamp);
}
