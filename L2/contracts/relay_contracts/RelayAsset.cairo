%lang starknet

from contracts.interfaces.IAsset import IAsset
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

from contracts.DataTypes import Asset, AssetWID
from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.Constants import ManageAssets_ACTION

// @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt, index_: felt
) {
    initialize(registry_address_, version_, index_);
    return ();
}

// @notice - All the following are mirror functions for Asset.cairo - just record call details and forward call

//#####################
// External functions #
//#####################

@external
func add_asset{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id: felt, new_asset: Asset
) {
    verify_caller_authority(ManageAssets_ACTION);
    record_call_details('add_asset');
    let (inner_address) = get_inner_contract();
    IAsset.add_asset(inner_address, id, new_asset);
    return ();
}

@external
func remove_asset{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(id: felt) {
    verify_caller_authority(ManageAssets_ACTION);
    record_call_details('remove_asset');
    let (inner_address) = get_inner_contract();
    IAsset.remove_asset(inner_address, id);
    return ();
}

@external
func modify_core_settings{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id: felt, short_name: felt, tradable: felt, collateral: felt, metadata_id: felt
) {
    verify_caller_authority(ManageAssets_ACTION);
    record_call_details('modify_core_settings');
    let (inner_address) = get_inner_contract();
    IAsset.modify_core_settings(inner_address, id, short_name, tradable, collateral, metadata_id);
    return ();
}

@external
func modify_trade_settings{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id: felt,
    tick_size: felt,
    step_size: felt,
    minimum_order_size: felt,
    minimum_leverage: felt,
    maximum_leverage: felt,
    currently_allowed_leverage: felt,
    maintenance_margin_fraction: felt,
    initial_margin_fraction: felt,
    incremental_initial_margin_fraction: felt,
    incremental_position_size: felt,
    baseline_position_size: felt,
    maximum_position_size: felt,
) {
    verify_caller_authority(ManageAssets_ACTION);
    record_call_details('modify_trade_settings');
    let (inner_address) = get_inner_contract();
    IAsset.modify_trade_settings(
        inner_address,
        id,
        tick_size,
        step_size,
        minimum_order_size,
        minimum_leverage,
        maximum_leverage,
        currently_allowed_leverage,
        maintenance_margin_fraction,
        initial_margin_fraction,
        incremental_initial_margin_fraction,
        incremental_position_size,
        baseline_position_size,
        maximum_position_size,
    );
    return ();
}

//#################
// View functions #
//#################

@view
func get_asset{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(id: felt) -> (
    currAsset: Asset
) {
    let (inner_address) = get_inner_contract();
    let (res) = IAsset.get_asset(inner_address, id);
    return (res,);
}

@view
func get_maintenance_margin{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id: felt
) -> (maintenance_margin: felt) {
    let (inner_address) = get_inner_contract();
    let (res) = IAsset.get_maintenance_margin(inner_address, id);
    return (res,);
}

@view
func get_version{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    version: felt
) {
    let (inner_address) = get_inner_contract();
    let (res) = IAsset.get_version(inner_address);
    return (res,);
}

@view
func return_all_assets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    array_list_len: felt, array_list: AssetWID*
) {
    let (inner_address) = get_inner_contract();
    let (array_list_len, array_list: AssetWID*) = IAsset.return_all_assets(inner_address);
    return (array_list_len, array_list);
}
