%lang starknet

from contracts.interfaces.IMarkets import IMarkets
from contracts.libraries.RelayLibrary import (
    record_call_details,
    get_inner_contract,
    initialize,
    verify_caller_authority,
)
from contracts.DataTypes import Market, MarketWID
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

@external
func add_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id: felt, newMarket: Market
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('add_market');
    let (inner_address) = get_inner_contract();
    IMarkets.add_market(contract_address=inner_address, id=id, newMarket=newMarket);
    return ();
}

@external
func remove_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(id: felt) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('remove_market');
    let (inner_address) = get_inner_contract();
    IMarkets.remove_market(contract_address=inner_address, id=id);
    return ();
}

@external
func modify_leverage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id: felt, leverage: felt
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('modify_leverage');
    let (inner_address) = get_inner_contract();
    IMarkets.modify_leverage(contract_address=inner_address, id=id, leverage=leverage);
    return ();
}

@external
func modify_tradable{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id: felt, tradable: felt
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('modify_tradable');
    let (inner_address) = get_inner_contract();
    IMarkets.modify_tradable(contract_address=inner_address, id=id, tradable=tradable);
    return ();
}

@external
func change_max_leverage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_max_leverage: felt
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('change_max_leverage');
    let (inner_address) = get_inner_contract();
    IMarkets.change_max_leverage(contract_address=inner_address, new_max_leverage=new_max_leverage);
    return ();
}

@external
func change_max_ttl{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_max_ttl: felt
) {
    verify_caller_authority(ManageMarkets_ACTION);
    record_call_details('change_max_ttl');
    let (inner_address) = get_inner_contract();
    IMarkets.change_max_ttl(contract_address=inner_address, new_max_ttl=new_max_ttl);
    return ();
}

@view
func get_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(id: felt) -> (
    currMarket: Market
) {
    let (inner_address) = get_inner_contract();
    let (currMarket) = IMarkets.get_market(contract_address=inner_address, id=id);
    return (currMarket,);
}

@view
func get_market_from_assets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id: felt, collateral_id: felt
) -> (market_id: felt) {
    let (inner_address) = get_inner_contract();
    let (market_id) = IMarkets.get_market_from_assets(
        contract_address=inner_address, asset_id=asset_id, collateral_id=collateral_id
    );
    return (market_id,);
}

@view
func get_all_markets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    array_list_len: felt, array_list: MarketWID*
) {
    let (inner_address) = get_inner_contract();
    let (array_list_len, array_list: MarketWID*) = IMarkets.get_all_markets(
        contract_address=inner_address
    );
    return (array_list_len, array_list);
}
