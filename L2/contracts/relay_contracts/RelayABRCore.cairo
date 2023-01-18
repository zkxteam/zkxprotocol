%lang starknet

from contracts.interfaces.IABRCore import IABRCore
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
)

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
func set_no_of_users_per_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_no_of_users_per_batch: felt
) {
    alloc_locals;

    record_call_details('set_no_of_users_per_batch');
    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    let (inner_address) = get_inner_contract();
    let () = IABRCore.set_no_of_users_per_batch(
        contract_address=inner_address, new_no_of_users_per_batch=new_no_of_users_per_batch
    );

    return ();
}

@external
func set_current_abr_timestamp{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_timestamp: felt
) {
    alloc_locals;

    record_call_details('set_current_abr_timestamp');
    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    let (inner_address) = get_inner_contract();
    let () = IABRCore.set_current_abr_timestamp(
        contract_address=inner_address, new_timestamp=new_timestamp
    );

    return ();
}

@external
func set_abr_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, perp_index_len: felt, perp_index: felt*, perp_mark_len: felt, perp_mark: felt*
) {
    alloc_locals;

    record_call_details('set_abr_value');
    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    let (inner_address) = get_inner_contract();
    let () = IABRCore.set_abr_value(
        contract_address=inner_address,
        market_id_=market_id_,
        perp_index_len=perp_index_len,
        perp_index=perp_index,
        perp_mark_len=perp_mark_len,
        perp_mark=perp_mark,
    );

    return ();
}

@external
func make_abr_payments{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() {
    alloc_locals;

    record_call_details('make_abr_payments');
    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    let (inner_address) = get_inner_contract();
    let () = IABRCore.make_abr_payments(contract_address=inner_address);

    return ();
}

@view
func get_state{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (res: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = IABRCore.get_state(contract_address=inner_address);
    return (res,);
}

@view
func get_epoch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (res: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = IABRCore.get_epoch(contract_address=inner_address);
    return (res,);
}

@view
func get_abr_interval{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (inner_address) = get_inner_contract();
    let (res) = IABRCore.get_abr_interval(contract_address=inner_address);
    return (res,);
}

@view
func get_markets_remaining{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    remaining_markets_list_len: felt, remaining_markets_list: felt*
) {
    let (inner_address) = get_inner_contract();
    let (
        remaining_markets_list_len: felt, remaining_markets_list: felt*
    ) = IABRCore.get_markets_remaining(contract_address=inner_address);
    return (remaining_markets_list_len, remaining_markets_list);
}

@view
func get_no_of_batches_for_current_epoch{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}() -> (res: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = IABRCore.get_no_of_batches_for_current_epoch(contract_address=inner_address);
    return (res,);
}

@view
func get_no_of_users_per_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    ) -> (res: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = IABRCore.get_no_of_users_per_batch(contract_address=inner_address);
    return (res,);
}

@view
func get_remaining_pay_abr_calls{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    ) -> (res: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = IABRCore.get_remaining_pay_abr_calls(contract_address=inner_address);
    return (res,);
}

@view
func get_next_abr_timestamp{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (inner_address) = get_inner_contract();
    let (res) = IABRCore.get_next_abr_timestamp(contract_address=inner_address);
    return (res,);
}
