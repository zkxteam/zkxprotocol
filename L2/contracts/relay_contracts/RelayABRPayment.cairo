%lang starknet

from contracts.interfaces.IABRPayment import IABRPayment
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

// @notice - All the following are mirror functions for ABRPayment.cairo - just record call details and forward call

@external
func pay_abr{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_addresses_len: felt, account_addresses: felt*
) {
    alloc_locals;

    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    record_call_details('pay_abr');
    let (inner_address) = get_inner_contract();
    IABRPayment.pay_abr(inner_address, account_addresses_len, account_addresses);
    return ();
}
