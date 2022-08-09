%lang starknet

from contracts.DataTypes import Asset, AssetWID
from contracts.Constants import (
    AdminAuth_INDEX,
    RiskManagement_INDEX,
    ManageAssets_ACTION,
)
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.libraries.Utils import verify_caller_authority
from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.messages import send_message_to_l1
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.bool import TRUE, FALSE

const ADD_ASSET = 1
const REMOVE_ASSET = 2

###########
# Storage #
###########

# Contract version
@storage_var
func contract_version() -> (version : felt):
end

# Address of AuthorizedRegistry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# Address of L1 ZKX contract
@storage_var
func L1_zkx_address() -> (res : felt):
end

# Version of Asset contract to refresh in node
@storage_var
func version() -> (res : felt):
end

# Length of assets array
@storage_var
func assets_array_len() -> (len : felt):
end

# Array of asset IDs
@storage_var
func asset_id_by_index(index : felt) -> (asset_id : felt):
end

# Mapping between asset ID and asset's index
@storage_var
func asset_index_by_id(asset_id : felt) -> (index : felt):
end

# Mapping between asset ID and asset's data
@storage_var
func asset_by_id(asset_id : felt) -> (res : Asset):
end

# Bool indicating if ID already exists
@storage_var
func asset_id_exists(asset_id : felt) -> (res : felt):
end

# Bool indicating if ticker already exists
@storage_var
func asset_ticker_exists(ticker : felt) -> (res : felt):
end

###############
# Constructor #
###############

# @notice Constructor of the smart-contract
# @param registry_address_ Address of the AuthorizedRegistry contract
# @param version_ Version of this contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):
    registry_address.write(registry_address_)
    contract_version.write(version_)
    return ()
end

##################
# View functions #
##################

# @notice get L1 ZKX contract address function
@view
func get_L1_zkx_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (res) = L1_zkx_address.read()
    return (res)
end

# @notice Getter function for Assets
# @param id - random string generated by zkxnode's mongodb
# @return currAsset - Returns the requested asset
@view
func getAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt
) -> (currAsset : Asset):
    _verify_asset_id_exists(id, should_exist=TRUE)
    let (asset : Asset) = asset_by_id.read(id)
    return (asset)
end

# @notice Return the maintenance margin for the asset
# @param id - Id of the asset
# @return maintenance_margin - Returns the maintenance margin of the asset
@view
func get_maintenance_margin{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt
) -> (maintenance_margin : felt):
    _verify_asset_id_exists(id, should_exist=TRUE)
    let (asset : Asset) = asset_by_id.read(id)
    return (asset.maintenance_margin_fraction)
end

# @notice Getter function for getting version
# @return - Returns the version
@view
func get_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    version : felt
):
    let (res) = version.read()
    return (res)
end

# @notice View function to return all the assets with ids in an array
# @returns array_list_len - Number of assets
# @returns array_list - Fully populated list of assets
@view
func returnAllAssets{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    array_list_len : felt, array_list : AssetWID*
):
    let (final_len) = assets_array_len.read()
    let (asset_list : AssetWID*) = alloc()
    return _populate_asset_list(0, final_len, asset_list)
end

######################
# External functions #
######################

# @notice set L1 ZKX contract address function
# @param address - L1 ZKX contract address as an argument
@external
func set_L1_zkx_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    l1_zkx_address : felt
):
    _verify_caller_authority()
    L1_zkx_address.write(l1_zkx_address)
    return ()
end

# @notice Add asset function
# @param id - random string generated by zkxnode's mongodb
# @param new_asset - Asset struct variable with the required details
@external
func addAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt, new_asset : Asset
):
    alloc_locals

    # Verify authority, state and input
    assert_not_zero(id)
    _verify_caller_authority()
    _verify_asset_id_exists(id, should_exist=FALSE)
    _verify_ticker_exists(new_asset.ticker, should_exist=FALSE)
    _validate_asset_properties(new_asset)

    # Save asset_id
    let (curr_len) = assets_array_len.read()
    asset_id_by_index.write(curr_len, id)
    asset_index_by_id.write(id, curr_len)
    assets_array_len.write(curr_len + 1)

    # Update id & ticker existence
    asset_id_exists.write(id, TRUE)
    asset_ticker_exists.write(new_asset.ticker, TRUE)

    # Save new_asset struct
    asset_by_id.write(id, new_asset)

    # Trigger asset update on L1
    _update_asset_on_L1(
        asset_id=id, 
        ticker=new_asset.ticker, 
        action=ADD_ASSET
    )
    
    return ()
end

# @notice Remove asset function
# @param id_to_remove - random string generated by zkxnode's mongodb
@external
func removeAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_to_remove : felt
):
    alloc_locals

    # Verify authority and state
    _verify_caller_authority()
    _verify_asset_id_exists(id_to_remove, should_exist=TRUE)
    
    # Prepare necessary data
    let (asset_to_remove : Asset) = asset_by_id.read(id_to_remove)
    local ticker_to_remove = asset_to_remove.ticker
    let (local index_to_remove) = asset_index_by_id.read(id_to_remove)
    let (local curr_len) = assets_array_len.read()
    local last_asset_index = curr_len - 1
    let (local last_asset_id) = asset_id_by_index.read(last_asset_index)

    # Replace id_to_remove with last_asset_id
    asset_id_by_index.write(index_to_remove, last_asset_id)
    asset_index_by_id.write(last_asset_id, index_to_remove)

    # Delete id_to_remove
    asset_id_by_index.write(last_asset_index, 0)
    assets_array_len.write(curr_len - 1)

    # Mark id & ticker as non-existing
    asset_id_exists.write(id_to_remove, FALSE)
    asset_ticker_exists.write(ticker_to_remove, FALSE)

    # Delete asset struct
    asset_by_id.write(id_to_remove, Asset(
        asset_version=0,
        ticker=0,
        short_name=0,
        tradable=0,
        collateral=0,
        token_decimal=0,
        metadata_id=0,
        tick_size=0,
        step_size=0,
        minimum_order_size=0,
        minimum_leverage=0,
        maximum_leverage=0,
        currently_allowed_leverage=0,
        maintenance_margin_fraction=0,
        initial_margin_fraction=0,
        incremental_initial_margin_fraction=0,
        incremental_position_size=0,
        baseline_position_size=0,
        maximum_position_size=0
    ))

    # Trigger asset update on L1
    _update_asset_on_L1(
        asset_id=id_to_remove, 
        ticker=ticker_to_remove, 
        action=REMOVE_ASSET
    )

    return ()
end

# @notice Modify core settings of asset function
# @param id - random string generated by zkxnode's mongodb
# @param short_name - new short_name for the asset
# @param tradable - new tradable flag value for the asset
# @param collateral - new collateral falg value for the asset
# @param token_decimal - It represents decimal point value of the token
# @param metadata_id - ID generated by asset metadata collection in zkx node
@external
func modify_core_settings{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt,
    short_name : felt,
    tradable : felt,
    collateral : felt,
    token_decimal : felt,
    metadata_id : felt,
):
    alloc_locals

    # Verify authority and state
    _verify_caller_authority()
    _verify_asset_id_exists(id, should_exist=TRUE)
    
    # Create updated_asset
    let (asset : Asset) = asset_by_id.read(id)
    local updated_asset: Asset = Asset(
        asset_version=asset.asset_version,
        ticker=asset.ticker,
        short_name=short_name,
        tradable=tradable,
        collateral=collateral,
        token_decimal=token_decimal,
        metadata_id=metadata_id,
        tick_size=asset.tick_size,
        step_size=asset.step_size,
        minimum_order_size=asset.minimum_order_size,
        minimum_leverage=asset.minimum_leverage,
        maximum_leverage=asset.maximum_leverage,
        currently_allowed_leverage=asset.currently_allowed_leverage,
        maintenance_margin_fraction=asset.maintenance_margin_fraction,
        initial_margin_fraction=asset.initial_margin_fraction,
        incremental_initial_margin_fraction=asset.incremental_initial_margin_fraction,
        incremental_position_size=asset.incremental_position_size,
        baseline_position_size=asset.baseline_position_size,
        maximum_position_size=asset.maximum_position_size
    )

    # Validate and save updated asset
    _validate_asset_properties(updated_asset)
    asset_by_id.write(id, updated_asset)

    return ()
end

# @notice Modify core settings of asset function
# @param id - random string generated by zkxnode's mongodb
# @param tick_size - new tradable flag value for the asset
# @param step_size - new collateral flag value for the asset
# @param minimum_order_size - new minimum_order_size value for the asset
# @param minimum_leverage - new minimum_leverage value for the asset
# @param maximum_leverage - new maximum_leverage value for the asset
# @param currently_allowed_leverage - new currently_allowed_leverage value for the asset
# @param maintenance_margin_fraction - new maintenance_margin_fraction value for the asset
# @param initial_margin_fraction - new initial_margin_fraction value for the asset
# @param incremental_initial_margin_fraction - new incremental_initial_margin_fraction value for the asset
# @param incremental_position_size - new incremental_position_size value for the asset
# @param baseline_position_size - new baseline_position_size value for the asset
# @param maximum_position_size - new maximum_position_size value for the asset
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
    alloc_locals

    # Verify authority and state
    _verify_caller_authority()
    _verify_asset_id_exists(id, should_exist=TRUE)

    # Create updated_asset
    let (asset : Asset) = asset_by_id.read(id)
    local updated_asset : Asset = Asset(
        asset_version=asset.asset_version + 1,
        ticker=asset.ticker,
        short_name=asset.short_name,
        tradable=asset.tradable,
        collateral=asset.collateral,
        token_decimal=asset.token_decimal,
        metadata_id=asset.metadata_id,
        tick_size=tick_size,
        step_size=step_size,
        minimum_order_size=minimum_order_size,
        minimum_leverage=minimum_leverage,
        maximum_leverage=maximum_leverage,
        currently_allowed_leverage=currently_allowed_leverage,
        maintenance_margin_fraction=maintenance_margin_fraction,
        initial_margin_fraction=initial_margin_fraction,
        incremental_initial_margin_fraction=incremental_initial_margin_fraction,
        incremental_position_size=incremental_position_size,
        baseline_position_size=baseline_position_size,
        maximum_position_size=maximum_position_size
    )

    # Validate and save updated asset
    _validate_asset_properties(updated_asset)
    asset_by_id.write(id, updated_asset)

    # Bump version
    let (curr_ver) = version.read()
    version.write(curr_ver + 1)

    return ()
end

######################
# Internal functions #
######################

# @notice Function to update asset list in L1
# @param asset_id - random string generated by zkxnode's mongodb
# @param ticker - Ticker of the asset
func _update_asset_on_L1{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id : felt, ticker : felt, action : felt
):
    # Build message payload
    let (message_payload : felt*) = alloc()
    assert message_payload[0] = action
    assert message_payload[1] = ticker
    assert message_payload[2] = asset_id

    # Send asset update message to L1
    let (L1_CONTRACT_ADDRESS) = get_L1_zkx_address()
    send_message_to_l1(to_address=L1_CONTRACT_ADDRESS, payload_size=3, payload=message_payload)

    return ()
end

# @notice Internal Function called by returnAllAssets to recursively add assets to the array and return it
# @param current_len - current length of array being populated
# @param final_len - final length of array being populated
# @param asset_array - array being populated with assets
# @returns array_list_len - Iterator used to populate array
# @returns array_list - Fully populated array of AssetWID
func _populate_asset_list{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    current_len : felt, final_len : felt, asset_array : AssetWID*
) -> (array_list_len : felt, array_list : AssetWID*):
    alloc_locals
    if current_len == final_len:
        return (final_len, asset_array)
    end
    let (id) = asset_id_by_index.read(current_len)
    let (asset : Asset) = asset_by_id.read(id)
    assert asset_array[current_len] = AssetWID(
        id=id,
        asset_version=asset.asset_version,
        ticker=asset.ticker,
        short_name=asset.short_name,
        tradable=asset.tradable,
        collateral=asset.collateral,
        token_decimal=asset.token_decimal,
        metadata_id=asset.metadata_id,
        tick_size=asset.tick_size,
        step_size=asset.step_size,
        minimum_order_size=asset.minimum_order_size,
        minimum_leverage=asset.minimum_leverage,
        maximum_leverage=asset.maximum_leverage,
        currently_allowed_leverage=asset.currently_allowed_leverage,
        maintenance_margin_fraction=asset.maintenance_margin_fraction,
        initial_margin_fraction=asset.initial_margin_fraction,
        incremental_initial_margin_fraction=asset.incremental_initial_margin_fraction,
        incremental_position_size=asset.incremental_position_size,
        baseline_position_size=asset.baseline_position_size,
        maximum_position_size=asset.maximum_position_size,
    )
    return _populate_asset_list(current_len + 1, final_len, asset_array)
end

func _verify_caller_authority{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}():
    with_attr error_message("Caller not authorized to manage assets"):
        let (registry) = registry_address.read()
        let (version) = contract_version.read()
        verify_caller_authority(registry, version, ManageAssets_ACTION)
    end
    return ()
end

func _verify_asset_id_exists{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id : felt, should_exist : felt
):
    with_attr error_message("asset_id existence mismatch"):
        let (id_exists) = asset_id_exists.read(asset_id)
        assert id_exists = should_exist
    end
    return ()
end

func _verify_ticker_exists{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ticker : felt, should_exist : felt
):
    with_attr error_message("ticker existence mismatch"):
        let (ticker_exists) = asset_ticker_exists.read(ticker)
        assert ticker_exists = should_exist
    end
    return ()
end

func _validate_asset_properties{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset : Asset
):  
    # TODO: add asset properties validation https://thalidao.atlassian.net/browse/ZKX-623
    return ()
end
