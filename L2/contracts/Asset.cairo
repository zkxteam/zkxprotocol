%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.messages import send_message_to_l1
from starkware.starknet.common.syscalls import get_caller_address, get_contract_address

from contracts.Constants import AdminAuth_INDEX, L1_ZKX_Address_INDEX, ManageAssets_ACTION
from contracts.DataTypes import Asset, AssetWID
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.Utils import verify_caller_authority

#############
# Constants #
#############

const ADD_ASSET = 1
const REMOVE_ASSET = 2

##########
# Events #
##########

# Event emitted on Asset contract deployment
@event
func asset_contract_created(
    contract_address : felt, registry_address : felt, version : felt, caller_address : felt
):
end

# Event emitted whenever new asset is added
@event
func asset_added(asset_id : felt, ticker : felt, caller_address : felt):
end

# Event emitted whenever asset is removed
@event
func asset_removed(asset_id : felt, ticker : felt, caller_address : felt):
end

# Event emitted whenever asset core settings are updated
@event
func asset_core_settings_update(asset_id : felt, ticker : felt, caller_address : felt):
end

# Event emitted whenever asset trade settings are updated
@event
func asset_trade_settings_update(
    asset_id : felt,
    ticker : felt,
    new_contract_version : felt,
    new_asset_version : felt,
    caller_address : felt,
):
end

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
    # Validate arguments
    with_attr error_message("Registry address or version used for Asset deployment is 0"):
        assert_not_zero(registry_address_)
        assert_not_zero(version_)
    end

    # Initialize storage
    registry_address.write(registry_address_)
    contract_version.write(version_)

    # Emit event
    let (contract_address) = get_contract_address()
    let (caller_address) = get_caller_address()
    asset_contract_created.emit(contract_address, registry_address_, version_, caller_address)

    return ()
end

##################
# View functions #
##################

# @notice View function for Assets
# @param id_ - random string generated by zkxnode's mongodb
# @return currAsset - Returns the requested asset
@view
func get_asset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(id_ : felt) -> (
    currAsset : Asset
):
    verify_asset_id_exists(id_, should_exist_=TRUE)
    let (asset : Asset) = asset_by_id.read(id_)
    return (asset)
end

# @notice View function to get the maintenance margin for the asset
# @param id_ - Id of the asset
# @return maintenance_margin - Returns the maintenance margin of the asset
@view
func get_maintenance_margin{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt
) -> (maintenance_margin : felt):
    verify_asset_id_exists(id_, should_exist_=TRUE)
    let (asset : Asset) = asset_by_id.read(id_)
    return (asset.maintenance_margin_fraction)
end

# @notice View function for getting version
# @return - Returns the version
@view
func get_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    version : felt
):
    let (res) = version.read()
    return (res)
end

# @notice View function to return all the assets with ids in an array
# @return array_list_len - Number of assets
# @return array_list - Fully populated list of assets
@view
func return_all_assets{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    array_list_len : felt, array_list : AssetWID*
):
    let (final_len) = assets_array_len.read()
    let (asset_list : AssetWID*) = alloc()
    return populate_asset_list(0, final_len, asset_list)
end

######################
# External functions #
######################

# @notice Add asset function
# @param id_ - random string generated by zkxnode's mongodb
# @param new_asset_ - Asset struct variable with the required details
@external
func addAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt, new_asset_ : Asset
):
    alloc_locals

    # Verify authority, state and input
    assert_not_zero(id_)
    verify_caller_authority_asset()
    verify_asset_id_exists(id_, should_exist_=FALSE)
    verify_ticker_exists(new_asset_.ticker, should_exist_=FALSE)
    validate_asset_properties(new_asset_)

    # Save asset_id
    let (curr_len) = assets_array_len.read()
    asset_id_by_index.write(curr_len, id_)
    asset_index_by_id.write(id_, curr_len)
    assets_array_len.write(curr_len + 1)

    # Update id & ticker existence
    asset_id_exists.write(id_, TRUE)
    asset_ticker_exists.write(new_asset_.ticker, TRUE)

    # Save new_asset struct
    asset_by_id.write(id_, new_asset_)

    # Trigger asset update on L1
    update_asset_on_L1(asset_id_=id_, ticker_=new_asset_.ticker, action_=ADD_ASSET)

    # Emit event
    let (caller_address) = get_caller_address()
    asset_added.emit(asset_id=id_, ticker=new_asset_.ticker, caller_address=caller_address)

    return ()
end

# @notice Remove asset function
# @param id_to_remove_ - random string generated by zkxnode's mongodb
@external
func removeAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_to_remove_ : felt
):
    alloc_locals

    # Verify authority and state
    verify_caller_authority_asset()
    verify_asset_id_exists(id_to_remove_, should_exist_=TRUE)

    # Prepare necessary data
    let (asset_to_remove : Asset) = asset_by_id.read(id_to_remove_)
    local ticker_to_remove = asset_to_remove.ticker
    let (local index_to_remove) = asset_index_by_id.read(id_to_remove_)
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
    asset_id_exists.write(id_to_remove_, FALSE)
    asset_ticker_exists.write(ticker_to_remove, FALSE)

    # Delete asset struct
    asset_by_id.write(
        id_to_remove_,
        Asset(
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
        ),
    )

    # Trigger asset update on L1
    update_asset_on_L1(asset_id_=id_to_remove_, ticker_=ticker_to_remove, action_=REMOVE_ASSET)

    # Emit event
    let (caller_address) = get_caller_address()
    asset_removed.emit(
        asset_id=id_to_remove_, ticker=ticker_to_remove, caller_address=caller_address
    )

    return ()
end

# @notice Modify core settings of asset function
# @param id_ - random string generated by zkxnode's mongodb
# @param short_name_ - new short_name for the asset
# @param tradable_ - new tradable flag value for the asset
# @param collateral_ - new collateral falg value for the asset
# @param token_decimal_ - It represents decimal point value of the token
# @param metadata_id_ - ID generated by asset metadata collection in zkx node
@external
func modify_core_settings{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt,
    short_name_ : felt,
    tradable_ : felt,
    collateral_ : felt,
    token_decimal_ : felt,
    metadata_id_ : felt,
):
    alloc_locals

    # Verify authority and state
    verify_caller_authority_asset()
    verify_asset_id_exists(id_, should_exist_=TRUE)

    # Create updated_asset
    let (asset : Asset) = asset_by_id.read(id_)
    local updated_asset : Asset = Asset(
        asset_version=asset.asset_version,
        ticker=asset.ticker,
        short_name=short_name_,
        tradable=tradable_,
        collateral=collateral_,
        token_decimal=token_decimal_,
        metadata_id=metadata_id_,
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
    validate_asset_properties(updated_asset)
    asset_by_id.write(id_, updated_asset)

    # Emit event
    let (caller_address) = get_caller_address()
    asset_core_settings_update.emit(
        asset_id=id_, ticker=updated_asset.ticker, caller_address=caller_address
    )

    return ()
end

# @notice Modify core settings of asset function
# @param id_ - random string generated by zkxnode's mongodb
# @param tick_size_ - new tradable flag value for the asset
# @param step_size_ - new collateral flag value for the asset
# @param minimum_order_size_ - new minimum_order_size value for the asset
# @param minimum_leverage_ - new minimum_leverage value for the asset
# @param maximum_leverage_ - new maximum_leverage value for the asset
# @param currently_allowed_leverage_ - new currently_allowed_leverage value for the asset
# @param maintenance_margin_fraction_ - new maintenance_margin_fraction value for the asset
# @param initial_margin_fraction_ - new initial_margin_fraction value for the asset
# @param incremental_initial_margin_fraction_ - new incremental_initial_margin_fraction value for the asset
# @param incremental_position_size_ - new incremental_position_size value for the asset
# @param baseline_position_size_ - new baseline_position_size value for the asset
# @param maximum_position_size_ - new maximum_position_size value for the asset
@external
func modify_trade_settings{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt,
    tick_size_ : felt,
    step_size_ : felt,
    minimum_order_size_ : felt,
    minimum_leverage_ : felt,
    maximum_leverage_ : felt,
    currently_allowed_leverage_ : felt,
    maintenance_margin_fraction_ : felt,
    initial_margin_fraction_ : felt,
    incremental_initial_margin_fraction_ : felt,
    incremental_position_size_ : felt,
    baseline_position_size_ : felt,
    maximum_position_size_ : felt,
):
    alloc_locals

    # Verify authority and state
    verify_caller_authority_asset()
    verify_asset_id_exists(id_, should_exist_=TRUE)

    # Create updated_asset
    let (asset : Asset) = asset_by_id.read(id_)
    local updated_asset : Asset = Asset(
        asset_version=asset.asset_version + 1,
        ticker=asset.ticker,
        short_name=asset.short_name,
        tradable=asset.tradable,
        collateral=asset.collateral,
        token_decimal=asset.token_decimal,
        metadata_id=asset.metadata_id,
        tick_size=tick_size_,
        step_size=step_size_,
        minimum_order_size=minimum_order_size_,
        minimum_leverage=minimum_leverage_,
        maximum_leverage=maximum_leverage_,
        currently_allowed_leverage=currently_allowed_leverage_,
        maintenance_margin_fraction=maintenance_margin_fraction_,
        initial_margin_fraction=initial_margin_fraction_,
        incremental_initial_margin_fraction=incremental_initial_margin_fraction_,
        incremental_position_size=incremental_position_size_,
        baseline_position_size=baseline_position_size_,
        maximum_position_size=maximum_position_size_
        )

    # Validate and save updated asset
    validate_asset_properties(updated_asset)
    asset_by_id.write(id_, updated_asset)

    # Bump version
    let (local curr_ver) = version.read()
    version.write(curr_ver + 1)

    # Emit event
    let (caller_address) = get_caller_address()
    asset_trade_settings_update.emit(
        asset_id=id_,
        ticker=updated_asset.ticker,
        new_contract_version=curr_ver + 1,
        new_asset_version=updated_asset.asset_version,
        caller_address=caller_address,
    )

    return ()
end

######################
# Internal functions #
######################

# @notice Internal function to update asset list in L1
# @param asset_id_ - random string generated by zkxnode's mongodb
# @param ticker_ - Ticker of the asset
# @param action_ - It could be ADD_ASSET or REMOVE_ASSET action
func update_asset_on_L1{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, ticker_ : felt, action_ : felt
):
    # Build message payload
    let (message_payload : felt*) = alloc()
    assert message_payload[0] = action_
    assert message_payload[1] = ticker_
    assert message_payload[2] = asset_id_

    # Send asset update message to L1
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (L1_ZKX_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=L1_ZKX_Address_INDEX, version=version
    )
    send_message_to_l1(to_address=L1_ZKX_address, payload_size=3, payload=message_payload)

    return ()
end

# @notice Internal Function called by return_all_assets to recursively add assets to the array and return it
# @param current_len_ - current length of array being populated
# @param final_len_ - final length of array being populated
# @param asset_array_ - array being populated with assets
# @return array_list_len - Iterator used to populate array
# @return array_list - Fully populated array of AssetWID
func populate_asset_list{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    current_len_ : felt, final_len_ : felt, asset_array_ : AssetWID*
) -> (array_list_len : felt, array_list : AssetWID*):
    alloc_locals
    if current_len_ == final_len_:
        return (final_len_, asset_array_)
    end
    let (id) = asset_id_by_index.read(current_len_)
    let (asset : Asset) = asset_by_id.read(id)
    assert asset_array_[current_len_] = AssetWID(
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
    return populate_asset_list(current_len_ + 1, final_len_, asset_array_)
end

func verify_caller_authority_asset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}():
    with_attr error_message("Caller not authorized to manage assets"):
        let (registry) = registry_address.read()
        let (version) = contract_version.read()
        verify_caller_authority(registry, version, ManageAssets_ACTION)
    end
    return ()
end

func verify_asset_id_exists{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, should_exist_ : felt
):
    with_attr error_message("asset_id existence mismatch"):
        let (id_exists) = asset_id_exists.read(asset_id_)
        assert id_exists = should_exist_
    end
    return ()
end

func verify_ticker_exists{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ticker_ : felt, should_exist_ : felt
):
    with_attr error_message("Ticker existence mismatch"):
        let (ticker_exists) = asset_ticker_exists.read(ticker_)
        assert ticker_exists = should_exist_
    end
    return ()
end

func validate_asset_properties{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_ : Asset
):
    # TODO: add asset properties validation https://thalidao.atlassian.net/browse/ZKX-623
    return ()
end
