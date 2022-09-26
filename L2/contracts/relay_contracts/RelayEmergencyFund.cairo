%lang starknet

from contracts.interfaces.IEmergencyFund import IEmergencyFund
from contracts.libraries.RelayLibrary import (
    record_call_details,
    get_inner_contract,
    initialize,
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

// @notice - All the following are mirror functions for EmergencyFund.cairo - just record call details and forward call

@external
func fund{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('fund');
    let (inner_address) = get_inner_contract();
    IEmergencyFund.fund(inner_address, asset_id_, amount);
    return ();
}

@external
func defund{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('defund');
    let (inner_address) = get_inner_contract();
    IEmergencyFund.defund(inner_address, asset_id_, amount);
    return ();
}

@external
func fund_holding{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('fund_holding');
    let (inner_address) = get_inner_contract();
    IEmergencyFund.fund_holding(inner_address, asset_id_, amount);
    return ();
}

@external
func fund_liquidity{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('fund_liquidity');
    let (inner_address) = get_inner_contract();
    IEmergencyFund.fund_liquidity(inner_address, asset_id_, amount);
    return ();
}

@external
func fund_insurance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('fund_insurance');
    let (inner_address) = get_inner_contract();
    IEmergencyFund.fund_insurance(inner_address, asset_id_, amount);
    return ();
}

@external
func defund_holding{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('defund_holding');
    let (inner_address) = get_inner_contract();
    IEmergencyFund.defund_holding(inner_address, asset_id, amount);
    return ();
}

@external
func defund_insurance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('defund_insurance');
    let (inner_address) = get_inner_contract();
    IEmergencyFund.defund_insurance(inner_address, asset_id, amount);
    return ();
}

@external
func defund_liquidity{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id: felt, amount: felt
) {
    verify_caller_authority(ManageFunds_ACTION);
    record_call_details('defund_liquidity');
    let (inner_address) = get_inner_contract();
    IEmergencyFund.defund_liquidity(inner_address, asset_id, amount);
    return ();
}

@view
func balance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(asset_id_: felt) -> (
    amount: felt
) {
    let (inner_address) = get_inner_contract();
    let (res) = IEmergencyFund.balance(inner_address, asset_id_);
    return (res,);
}
