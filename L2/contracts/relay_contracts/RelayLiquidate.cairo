%lang starknet

from contracts.interfaces.ILiquidate import ILiquidate
from contracts.libraries.RelayLibrary import (
    get_inner_contract,
    initialize,
    record_call_details,
    get_call_counter,
)

from contracts.DataTypes import PositionDetailsForRiskManagement, MultipleOrder
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
func return_maintenance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (inner_address) = get_inner_contract();
    let (res) = ILiquidate.return_maintenance(inner_address);
    return (res,);
}

@view
func return_acc_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (inner_address) = get_inner_contract();
    let (res) = ILiquidate.return_acc_value(inner_address);
    return (res,);
}

// ///////////
// External //
// ///////////

@external
func check_for_risk{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_: MultipleOrder,
    size_: felt,
    execution_price_: felt,
    oracle_price_: felt,
    margin_amount_: felt,
    collateral_token_decimal_: felt,
) -> () {
    alloc_locals;

    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    local range_check_ptr = range_check_ptr;

    record_call_details('check_for_risk');
    let (inner_address) = get_inner_contract();
    ILiquidate.check_for_risk(
        inner_address,
        order_,
        size_,
        execution_price_,
        oracle_price_,
        margin_amount_,
        collateral_token_decimal_,
    );
    return ();
}

@external
func mark_under_collateralized_position{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(account_address_: felt, collateral_id_: felt) -> (
    liq_result: felt,
    least_collateral_ratio_position: PositionDetailsForRiskManagement,
    total_account_value: felt,
    total_maintenance_requirement: felt,
) {
    alloc_locals;

    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    local range_check_ptr = range_check_ptr;

    record_call_details('check_for_risk');
    let (inner_address) = get_inner_contract();
    let (
        liq_result: felt,
        least_collateral_ratio_position: PositionDetailsForRiskManagement,
        total_account_value: felt,
        total_maintenance_requirement: felt,
    ) = ILiquidate.mark_under_collateralized_position(
        contract_address=inner_address,
        account_address_=account_address_,
        collateral_id_=collateral_id_,
    );
    return (
        liq_result,
        least_collateral_ratio_position,
        total_account_value,
        total_maintenance_requirement,
    );
}
