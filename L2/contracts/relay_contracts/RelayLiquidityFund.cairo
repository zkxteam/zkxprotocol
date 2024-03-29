%lang starknet

from contracts.interfaces.ILiquidityFund import ILiquidityFund
from contracts.libraries.RelayLibrary import (
    record_call_details,
    get_inner_contract,
    initialize,
    verify_caller_authority,
)

from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.Constants import ManageFunds_ACTION

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
func balance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(asset_id_: felt) -> (
    amount: felt
) {
    let (inner_address) = get_inner_contract();
    let (res) = ILiquidityFund.balance(inner_address, asset_id_);
    return (res,);
}

@view
func liq_amount{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, position_id_: felt
) -> (amount: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = ILiquidityFund.liq_amount(inner_address, asset_id_, position_id_);
    return (res,);
}

// ///////////
// External //
// ///////////

// @notice - All the following are mirror functions for LiquidityFund.cairo - just record call details and forward call
@external
func fund{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('fund');
    let (inner_address) = get_inner_contract();
    ILiquidityFund.fund(inner_address, asset_id_, amount);
    return ();
}

@external
func defund{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('defund');
    let (inner_address) = get_inner_contract();
    ILiquidityFund.defund(inner_address, asset_id_, amount);
    return ();
}

@external
func deposit{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt, position_id_: felt
) {
    record_call_details('deposit');
    let (inner_address) = get_inner_contract();
    ILiquidityFund.deposit(inner_address, asset_id_, amount, position_id_);
    return ();
}

@external
func withdraw{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt, position_id_: felt
) {
    record_call_details('withdraw');
    let (inner_address) = get_inner_contract();
    ILiquidityFund.withdraw(inner_address, asset_id_, amount, position_id_);
    return ();
}
