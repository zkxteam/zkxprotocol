%lang starknet

from contracts.interfaces.ILiquidate import ILiquidate
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
verify_caller_authority
)

from contracts.DataTypes import PriceData
from starkware.cairo.common.cairo_builtins import HashBuiltin

// @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt, index_: felt
) {
    initialize(registry_address_, version_, index_);
    return ();
}

// @notice - All the following are mirror functions for Liquidate.cairo - just record call details and forward call

@external
func check_liquidation{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_address: felt, prices_len: felt, prices: PriceData*
) -> (liq_result: felt, least_collateral_ratio_position: felt) {
    alloc_locals;

    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    local range_check_ptr = range_check_ptr;

    record_call_details('check_liquidation');
    let (inner_address) = get_inner_contract();
    let (liq_result, least_collateral_ratio_position) = ILiquidate.check_liquidation(
        inner_address, account_address, prices_len, prices
    );
    return (liq_result, least_collateral_ratio_position);
}
