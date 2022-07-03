%lang starknet


from contracts.interfaces.IAsset import IAsset
from contracts.libraries.RelayLibrary import (
    record_call_details,
    get_inner_contract,
    initialize
)
from contracts.DataTypes import Asset, AssetWID
from starkware.cairo.common.cairo_builtins import HashBuiltin

# @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt, index_:felt):

    initialize(registry_address_,version_,index_)
    return ()
end

# @notice - All the following are mirror functions for Asset.cairo - just record call details and forward call

@external
func set_L1_zkx_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    l1_zkx_address : felt
):

    record_call_details('set_L1_zkx_address')
    let (inner_address)=get_inner_contract()
    IAsset.set_L1_zkx_address(inner_address,l1_zkx_address)
    return()
end

@external
func addAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt, newAsset : Asset
):
    record_call_details('addAsset')
    let (inner_address)=get_inner_contract()
    IAsset.addAsset(inner_address,id,newAsset)
    return()
end


@external
func removeAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(id : felt):
    record_call_details('removeAsset')
    let (inner_address)=get_inner_contract()
    IAsset.removeAsset(inner_address,id)
    return()
end

@external
func modify_core_settings{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt,
    short_name : felt,
    tradable : felt,
    collateral : felt,
    token_decimal : felt,
    metadata_id : felt,
):
    record_call_details('modify_core_settings')
    let (inner_address)=get_inner_contract()
    IAsset.modify_core_settings(
    inner_address,
    id,
    short_name,
    tradable,
    collateral,
    token_decimal,
    metadata_id,
    )
    return()
    
end


@external
func modify_trade_settings{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt,
    tick_size : felt,
    step_size : felt,
    minimum_order_size : felt,
    minimum_leverage : felt,
    maximum_leverage : felt,
    currently_allowed_leverage : felt,
    maintenance_margin_fraction : felt,
    initial_margin_fraction : felt,
    incremental_initial_margin_fraction : felt,
    incremental_position_size : felt,
    baseline_position_size : felt,
    maximum_position_size : felt,
):
    record_call_details('modify_trade_settings')
    let (inner_address)=get_inner_contract()
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
    maximum_position_size
    )
    return()

end

@view
func get_L1_zkx_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
   
    let (inner_address)=get_inner_contract()
    let (res)=IAsset.get_L1_zkx_address(inner_address)
    return(res)

end

@view
func getAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(id : felt) -> (
    currAsset : Asset
):
    let (inner_address)=get_inner_contract()
    let (res)=IAsset.getAsset(inner_address,id)
    return(res)
end

@view
func get_maintenance_margin{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt
) -> (maintenance_margin : felt):

    let (inner_address)=get_inner_contract()
    let (res)=IAsset.get_maintenance_margin(inner_address,id)
    return(res)
    
end


@view
func get_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    version : felt
):

    let (inner_address)=get_inner_contract()
    let (res)=IAsset.get_version(inner_address)
    return(res)
end

@view
func returnAllAssets{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    array_list_len : felt, array_list : AssetWID*
):

    let (inner_address)=get_inner_contract()
    let (array_list_len, array_list:AssetWID*)=IAsset.returnAllAssets(inner_address)
    return(array_list_len,array_list)

end