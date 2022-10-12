%lang starknet

from contracts.interfaces.IMarkets import IMarkets
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

from contracts.DataTypes import Market
from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.Constants import ManageMarkets_ACTION

// @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt, index_: felt
) {
    initialize(registry_address_, version_, index_);
    return ();
}

// @notice - All the following are mirror functions for Markets.cairo - just record call details and forward call

//////////////
// External //
//////////////

@external
func add_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_market_: Market
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('add_market');
    let (inner_address) = get_inner_contract();
    IMarkets.add_market(contract_address=inner_address, new_market_=new_market_);
    return ();
}

@external
func remove_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(market_id_: felt) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('remove_market');
    let (inner_address) = get_inner_contract();
    IMarkets.remove_market(inner_address, market_id_);
    return ();
}

@external
func modify_leverage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, leverage_: felt
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('modify_leverage');
    let (inner_address) = get_inner_contract();
    IMarkets.modify_leverage(inner_address, market_id_, leverage_);
    return ();
}

@external
func modify_tradable{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, is_tradable_: felt
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('modify_tradable');
    let (inner_address) = get_inner_contract();
    IMarkets.modify_tradable(inner_address, market_id_, is_tradable_);
    return ();
}

@external
func change_max_leverage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_max_leverage_: felt
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('change_max_leverage');
    let (inner_address) = get_inner_contract();
    IMarkets.change_max_leverage(inner_address, new_max_leverage_);
    return ();
}

@external
func change_max_ttl{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_max_ttl_: felt
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('change_max_ttl');
    let (inner_address) = get_inner_contract();
    IMarkets.change_max_ttl(inner_address, new_max_ttl_);
    return ();
}

@external
func modify_archived_state{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, is_archived_: felt
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('modify_archived_state');
    let (inner_address) = get_inner_contract();
    IMarkets.modify_archived_state(inner_address, market_id_, is_archived_);
    return ();
}

@external
func modify_trade_settings{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt,
    tick_size_: felt,
    step_size_: felt,
    minimum_order_size_: felt,
    minimum_leverage_: felt,
    maximum_leverage_: felt,
    currently_allowed_leverage_: felt,
    maintenance_margin_fraction_: felt,
    initial_margin_fraction_: felt,
    incremental_initial_margin_fraction_: felt,
    incremental_position_size_: felt,
    baseline_position_size_: felt,
    maximum_position_size_: felt
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('modify_trade_settings');
    let (inner_address) = get_inner_contract();
    IMarkets.modify_trade_settings(
        inner_address,
        market_id_,
        tick_size_,
        step_size_,
        minimum_order_size_,
        minimum_leverage_,
        maximum_leverage_,
        currently_allowed_leverage_,
        maintenance_margin_fraction_,
        initial_margin_fraction_,
        incremental_initial_margin_fraction_,
        incremental_position_size_,
        baseline_position_size_,
        maximum_position_size_
    );
    return ();
}

//////////
// View //
//////////

@view
func get_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(market_id_: felt) -> (
    currMarket: Market
) {
    let (inner_address) = get_inner_contract();
    let (currMarket) = IMarkets.get_market(inner_address, market_id_);
    return (currMarket,);
}

@view
func get_market_id_from_assets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, collateral_id_: felt
) -> (market_id: felt) {
    let (inner_address) = get_inner_contract();
    let (market_id) = IMarkets.get_market_id_from_assets(inner_address, asset_id_, collateral_id_);
    return (market_id,);
}

@view
func get_all_markets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    array_list_len: felt, array_list: Market*
) {
    let (inner_address) = get_inner_contract();
    let (array_list_len, array_list: Market*) = IMarkets.get_all_markets(inner_address);
    return (array_list_len, array_list);
}
