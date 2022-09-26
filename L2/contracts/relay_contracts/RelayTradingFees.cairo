%lang starknet

from contracts.interfaces.ITradingFees import ITradingFees
from contracts.libraries.RelayLibrary import (
    record_call_details,
    get_inner_contract,
    initialize,
    verify_caller_authority,
)
from contracts.DataTypes import BaseFee, Discount
from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.Constants import ManageFeeDetails_ACTION

// @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt, index_: felt
) {
    initialize(registry_address_, version_, index_);
    return ();
}

// @notice - All the following are mirror functions for TradingFees.cairo - just record call details and forward call

@external
func update_base_fees{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tier_: felt, fee_details: BaseFee
) {
    verify_caller_authority(ManageFeeDetails_ACTION);
    record_call_details('update_base_fees');
    let (inner_address) = get_inner_contract();
    ITradingFees.update_base_fees(inner_address, tier_, fee_details);
    return ();
}

@external
func update_discount{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tier_: felt, discount_details: Discount
) {
    verify_caller_authority(ManageFeeDetails_ACTION);
    record_call_details('update_discount');
    let (inner_address) = get_inner_contract();
    ITradingFees.update_discount(inner_address, tier_, discount_details);
    return ();
}

@external
func update_max_base_fee_tier{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tier_: felt
) {
    verify_caller_authority(ManageFeeDetails_ACTION);
    record_call_details('update_max_base_fee_tier');
    let (inner_address) = get_inner_contract();
    ITradingFees.update_max_base_fee_tier(inner_address, tier_);
    return ();
}

@external
func update_max_discount_tier{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tier_: felt
) {
    verify_caller_authority(ManageFeeDetails_ACTION);
    record_call_details('update_max_discount_tier');
    let (inner_address) = get_inner_contract();
    ITradingFees.update_max_discount_tier(inner_address, tier_);
    return ();
}

@view
func get_base_fees{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tier_: felt
) -> (base_fee: BaseFee) {
    let (inner_address) = get_inner_contract();
    let (res) = ITradingFees.get_base_fees(inner_address, tier_);
    return (res,);
}

@view
func get_discount{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(tier_: felt) -> (
    discount: Discount
) {
    let (inner_address) = get_inner_contract();
    let (res) = ITradingFees.get_discount(inner_address, tier_);
    return (res,);
}

@view
func get_max_base_fee_tier{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    value: felt
) {
    let (inner_address) = get_inner_contract();
    let (res) = ITradingFees.get_max_base_fee_tier(inner_address);
    return (res,);
}

@view
func get_max_discount_tier{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    value: felt
) {
    let (inner_address) = get_inner_contract();
    let (res) = ITradingFees.get_max_discount_tier(inner_address);
    return (res,);
}

@view
func get_user_fee_and_discount{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address_: felt, side_: felt
) -> (fee: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = ITradingFees.get_user_fee_and_discount(inner_address, address_, side_);
    return (res,);
}
