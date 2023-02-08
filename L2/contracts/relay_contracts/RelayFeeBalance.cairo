%lang starknet

from contracts.interfaces.IFeeBalance import IFeeBalance
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

from starkware.cairo.common.cairo_builtins import HashBuiltin

// //////////////
// Constructor //
// //////////////

// @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt, index_: felt
) {
    initialize(registry_address_, version_, index_);
    return ();
}

// ///////
// View //
// ///////

@view
func get_total_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    assetID_: felt
) -> (fee: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = IFeeBalance.get_total_fee(inner_address, assetID_);
    return (res,);
}

@view
func get_user_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address: felt, assetID_: felt
) -> (fee: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = IFeeBalance.get_user_fee(inner_address, address, assetID_);
    return (res,);
}

// ///////////
// External //
// ///////////

// @notice - All the following are mirror functions for FeeBalance.cairo - just record call details and forward call
@external
func update_fee_mapping{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address: felt, assetID_: felt, fee_to_add: felt
) {
    record_call_details('update_fee_mapping');
    let (inner_address) = get_inner_contract();
    IFeeBalance.update_fee_mapping(inner_address, address, assetID_, fee_to_add);
    return ();
}
