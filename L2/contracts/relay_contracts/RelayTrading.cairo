%lang starknet

from contracts.interfaces.ITrading import ITrading
from contracts.libraries.RelayLibrary import (
    record_call_details,
    get_inner_contract,
    initialize,
    get_current_version,
    get_caller_hash_status,
    get_call_counter,
    get_registry_address_at_relay,
    get_self_index,
    get_caller_hash_list,
    set_current_version,
    mark_caller_hash_paid,
    reset_call_counter,
    set_self_index,
    verify_caller_authority,
)

from contracts.DataTypes import MultipleOrder
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin

// @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt, index_: felt
) {
    initialize(registry_address_, version_, index_);
    return ();
}

// @notice - All the following are mirror functions for Trading.cairo - just record call details and forward call
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
) {
    alloc_locals;

    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    local range_check_ptr = range_check_ptr;
    local ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;

    record_call_details('execute_batch');
    let (inner_address) = get_inner_contract();
    ITrading.execute_batch(
        inner_address,
        batch_id_,
        quantity_locked_,
        market_id_,
        oracle_price_,
        request_list_len,
        request_list,
    );
    return ();
}

@view
func get_batch_id_status{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    batch_id_: felt
) -> (status: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = ITrading.get_batch_id_status(inner_address, batch_id_);
    return (res,);
}
