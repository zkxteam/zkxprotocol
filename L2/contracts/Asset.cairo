%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_in_range, assert_le, assert_not_zero
from starkware.starknet.common.messages import send_message_to_l1
from starkware.starknet.common.syscalls import get_caller_address, get_contract_address

from contracts.Constants import AdminAuth_INDEX, L1_ZKX_Address_INDEX, ManageAssets_ACTION
from contracts.DataTypes import Asset
from contracts.Math_64x61 import Math64x61_assertPositive64x61
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.StringLib import StringLib
from contracts.libraries.Validation import assert_bool
from contracts.libraries.Utils import verify_caller_authority

///////////////
// Constants //
///////////////

const ADD_ASSET = 1;
const REMOVE_ASSET = 2;
const ICON_LINK_TYPE = 'ICON_LINK_TYPE';
const METADATA_LINK_TYPE = 'METADATA_LINK_TYPE';

////////////
// Events //
////////////

// Event emitted on Asset contract deployment
@event
func asset_contract_created(
    contract_address: felt, registry_address: felt, version: felt, caller_address: felt
) {
}

// Event emitted whenever new asset is added
@event
func asset_added(asset_id: felt, ticker: felt, caller_address: felt) {
}

// Event emitted whenever asset is removed
@event
func asset_removed(asset_id: felt, ticker: felt, caller_address: felt) {
}

// Event emitted whenever asset core settings are updated
@event
func asset_core_settings_update(asset_id: felt, ticker: felt, caller_address: felt) {
}

// Event emitted when asset icon link is updated
@event
func asset_icon_link_update(asset_id: felt) {
}

// Event emitted when asset metadata link is updated
@event
func asset_metadata_link_update(asset_id: felt) {
}

/////////////
// Storage //
/////////////

// Version of Asset contract to refresh in node
@storage_var
func version() -> (res: felt) {
}

// Length of assets array
@storage_var
func assets_array_len() -> (len: felt) {
}

// Array of asset IDs
@storage_var
func asset_id_by_index(index: felt) -> (asset_id: felt) {
}

// Mapping between asset ID and asset's index
@storage_var
func asset_index_by_id(asset_id: felt) -> (index: felt) {
}

// Mapping between asset ID and asset's data
@storage_var
func asset_by_id(asset_id: felt) -> (res: Asset) {
}

// Bool indicating if ID already exists
@storage_var
func asset_id_exists(asset_id: felt) -> (res: felt) {
}

/////////////////
// Constructor //
/////////////////

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);

    // Emit event
    let (contract_address) = get_contract_address();
    let (caller_address) = get_caller_address();
    asset_contract_created.emit(contract_address, registry_address_, version_, caller_address);

    return ();
}

//////////
// View //
//////////

// @notice View function for Assets
// @param id - random string generated by zkxnode's mongodb
// @return currAsset - Returns the requested asset
@view
func get_asset{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(id: felt) -> (
    currAsset: Asset
) {
    verify_asset_id_exists(id, should_exist_=TRUE);
    let (asset: Asset) = asset_by_id.read(id);
    return (asset,);
}

// @notice View function for getting version
// @return - Returns the version
@view
func get_version{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    version: felt
) {
    let (res) = version.read();
    return (res,);
}

// @notice View function to return all the assets with ids in an array
// @return array_list_len - Number of assets
// @return array_list - Fully populated list of assets
@view
func return_all_assets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    array_list_len: felt, array_list: Asset*
) {
    let (final_len) = assets_array_len.read();
    let (asset_list: Asset*) = alloc();
    return populate_asset_list(0, final_len, asset_list);
}

// @notice View function to read asset icon link
// @return link_len - Length of link string
// @return link - Link characters
@view
func get_icon_link{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id: felt
) -> (link_len: felt, link: felt*) {
    let (link_len, link) = StringLib.read_string(type=ICON_LINK_TYPE, id=id);
    return (link_len, link);
}

// @notice View function to read asset metadata link
// @return link_len - Length of link string
// @return link - Link characters
@view
func get_metadata_link{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id: felt
) -> (link_len: felt, link: felt*) {
    let (link_len, link) = StringLib.read_string(type=METADATA_LINK_TYPE, id=id);
    return (link_len, link);
}

//////////////
// External //
//////////////

// @notice Add asset function
// @param id - random string generated by zkxnode's mongodb
// @param new_asset - Asset struct variable with the required details
@external
func add_asset{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id: felt, 
    new_asset: Asset, 
    icon_link_len: felt, 
    icon_link: felt*,
    metadata_link_len: felt,
    metadata_link: felt*
) {
    alloc_locals;

    // Verify authority, state and input
    verify_asset_manager_authority();
    verify_asset_id_exists(id, should_exist_=FALSE);

    with_attr error_message("Asset: problem with asset ID") {
        assert_not_zero(id);
        assert new_asset.id = id;
    }
    with_attr error_message("Asset: problem with asset core settings") {
        assert_bool(new_asset.is_collateral);
        assert_bool(new_asset.is_tradable);
        assert_in_range(new_asset.token_decimal, 1, 19);
    }

    // Save asset_id
    let (curr_len) = assets_array_len.read();
    asset_id_by_index.write(curr_len, id);
    asset_index_by_id.write(id, curr_len);
    assets_array_len.write(curr_len + 1);

    // Update id existence
    asset_id_exists.write(id, TRUE);

    // Save new_asset struct
    asset_by_id.write(id, new_asset);

    // Save asset links
    StringLib.save_string(
        type=ICON_LINK_TYPE, 
        id=id, 
        string_len=icon_link_len,
        string=icon_link
    );
    StringLib.save_string(
        type=METADATA_LINK_TYPE, 
        id=id, 
        string_len=metadata_link_len,
        string=metadata_link
    );

    // Trigger asset update on L1
    update_asset_on_L1(asset_id_=id, action_=ADD_ASSET);

    // Emit event
    let (caller_address) = get_caller_address();
    asset_added.emit(asset_id=id, caller_address=caller_address);

    return ();
}

// @notice Remove asset function
// @param id_to_remove_ - random string generated by zkxnode's mongodb
@external
func remove_asset{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id_to_remove: felt
) {
    alloc_locals;

    // Verify authority and state
    verify_asset_manager_authority();
    verify_asset_id_exists(id_to_remove, should_exist_=TRUE);

    // Prepare necessary data
    let (asset_to_remove: Asset) = asset_by_id.read(id_to_remove);
    let (local index_to_remove) = asset_index_by_id.read(id_to_remove);
    let (local curr_len) = assets_array_len.read();
    local last_asset_index = curr_len - 1;
    let (local last_asset_id) = asset_id_by_index.read(last_asset_index);

    // Replace id_to_remove with last_asset_id
    asset_id_by_index.write(index_to_remove, last_asset_id);
    asset_index_by_id.write(last_asset_id, index_to_remove);

    // Delete id_to_remove
    asset_id_by_index.write(last_asset_index, 0);
    assets_array_len.write(curr_len - 1);

    // Mark id as non-existing
    asset_id_exists.write(id_to_remove, FALSE);

    // Delete asset struct
    asset_by_id.write(id_to_remove, Asset(
        id=0,
        asset_version=0,
        ticker=0,
        short_name=0,
        is_tradable=0,
        is_collateral=0,
        token_decimal=0
    ));

    // Delete asset links
    StringLib.remove_existing_string(type=ICON_LINK_TYPE, id=id_to_remove);
    StringLib.remove_existing_string(type=METADATA_LINK_TYPE, id=id_to_remove);

    // Trigger asset update on L1
    update_asset_on_L1(asset_id_=id_to_remove, action_=REMOVE_ASSET);

    // Emit event
    let (caller_address) = get_caller_address();
    asset_removed.emit(asset_id=id_to_remove, caller_address=caller_address);

    return ();
}

// @notice Modify core settings of asset function
// @param id_ - random string generated by zkxnode's mongodb
// @param short_name_ - new short_name for the asset
// @param is_tradable_ - new tradable flag value for the asset
// @param is_collateral_ - new collateral falg value for the asset
@external
func modify_core_settings{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id_: felt, short_name_: felt, is_tradable_: felt, is_collateral_: felt
) {
    alloc_locals;

    // Verify authority and state
    verify_asset_manager_authority();
    verify_asset_id_exists(id_, should_exist_=TRUE);
    with_attr error_message("Asset: is_tradable_ & is_collateral_ must be bool") {
        assert_bool(is_collateral_);
        assert_bool(is_tradable_);
    }

    // Create updated_asset
    let (asset: Asset) = asset_by_id.read(id_);
    local updated_asset: Asset = Asset(
        id=asset.id,
        asset_version=asset.asset_version,
        ticker=asset.ticker,
        short_name=short_name_,
        is_tradable=is_tradable_,
        is_collateral=is_collateral_,
        token_decimal=asset.token_decimal
    );

    // Save updated asset
    asset_by_id.write(id_, updated_asset);

    // Emit event
    let (caller_address) = get_caller_address();
    asset_core_settings_update.emit(
        asset_id=id_, ticker=updated_asset.ticker, caller_address=caller_address
    );

    return ();
}

// @notice Update asset's icon link
// @param asset_id - ID of Asset to be updated
// @param link_len - Length of a link
// @param link - Link characters
@external
func update_icon_link{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id: felt, link_len: felt, link: felt*
) {
    StringLib.remove_existing_string(type=ICON_LINK_TYPE, id=asset_id);
    StringLib.save_string(
        type=ICON_LINK_TYPE, 
        id=asset_id,
        string_len=link_len,
        string=link
    );
    asset_icon_link_update.emit(asset_id);
    return ();
}

// @notice Update asset's metadata link
// @param asset_id - ID of Asset to be updated
// @param link_len - Length of a link
// @param link - Link characters
@external
func update_metadata_link{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id: felt, link_len: felt, link: felt*
) {
    StringLib.remove_existing_string(type=METADATA_LINK_TYPE, id=asset_id);
    StringLib.save_string(
        type=METADATA_LINK_TYPE, 
        id=asset_id, 
        string_len=link_len,
        string=link
    );
    asset_metadata_link_update.emit(asset_id);
    return ();
}

//////////////
// Internal //
//////////////

// @notice Internal function to update asset list in L1
// @param asset_id_ - random string generated by zkxnode's mongodb
// @param ticker_ - Ticker of the asset
// @param action_ - It could be ADD_ASSET or REMOVE_ASSET action
func update_asset_on_L1{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, ticker_: felt, action_: felt
) {
    // Build message payload
    let (message_payload: felt*) = alloc();
    assert message_payload[0] = action_;
    assert message_payload[1] = ticker_;
    assert message_payload[2] = asset_id_;

    // Send asset update message to L1
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (L1_ZKX_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=L1_ZKX_Address_INDEX, version=version
    );
    send_message_to_l1(to_address=L1_ZKX_address, payload_size=3, payload=message_payload);

    return ();
}

// @notice Internal Function called by return_all_assets to recursively add assets to the array and return it
// @param current_len_ - current length of array being populated
// @param final_len_ - final length of array being populated
// @param asset_array_ - array being populated with assets
// @return array_list_len - Iterator used to populate array
// @return array_list - Fully populated array of assets
func populate_asset_list{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    current_len_: felt, final_len_: felt, asset_array_: Asset*
) -> (array_list_len: felt, array_list: Asset*) {
    alloc_locals;
    if (current_len_ == final_len_) {
        return (final_len_, asset_array_);
    }
    let (id) = asset_id_by_index.read(current_len_);
    let (asset: Asset) = asset_by_id.read(id);
    assert asset_array_[current_len_] = Asset(
        id=id,
        asset_version=asset.asset_version,
        ticker=asset.ticker,
        short_name=asset.short_name,
        tradable=asset.tradable,
        collateral=asset.collateral,
        token_decimal=asset.token_decimal
    );
    return populate_asset_list(current_len_ + 1, final_len_, asset_array_);
}

func verify_asset_manager_authority{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    ) {
    with_attr error_message("Asset: caller not authorized to manage assets") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, ManageAssets_ACTION);
    }
    return ();
}

func verify_asset_id_exists{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, should_exist_: felt
) {
    with_attr error_message("Asset: asset_id existence check failed") {
        let (id_exists) = asset_id_exists.read(asset_id_);
        assert id_exists = should_exist_;
    }
    return ();
}
