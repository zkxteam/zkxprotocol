%lang starknet

from contracts.interfaces.IHolding import IHolding
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
from contracts.Constants import ManageFunds_ACTION

// @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt, index_: felt
) {
    initialize(registry_address_, version_, index_);
    return ();
}

// @notice - All the following are mirror functions for Holding.cairo - just record call details and forward call

@external
func fund{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('fund');
    let (inner_address) = get_inner_contract();
    IHolding.fund(inner_address, asset_id_, amount);
    return ();
}

@external
func defund{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('defund');
    let (inner_address) = get_inner_contract();
    IHolding.defund(inner_address, asset_id_, amount);
    return ();
}

@external
func deposit{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    record_call_details('deposit');
    let (inner_address) = get_inner_contract();
    IHolding.deposit(inner_address, asset_id_, amount);
    return ();
}

@external
func withdraw{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    record_call_details('withdraw');
    let (inner_address) = get_inner_contract();
    IHolding.withdraw(inner_address, asset_id_, amount);
    return ();
}

@view
func balance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(asset_id_: felt) -> (
    amount: felt
) {
    let (inner_address) = get_inner_contract();
    let (res) = IHolding.balance(inner_address, asset_id_);
    return (res,);
}
