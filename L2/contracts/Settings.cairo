%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address, get_contract_address

from contracts.Constants import ManageSettings_ACTION
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.StringLib import StringLib
from contracts.libraries.Utils import verify_master_admin_or_authority

///////////////
// Constants //
///////////////

const SETTINGS_LINK_TYPE = 'SETTINGS_LINK_TYPE';
const LINK_ID = 0;

////////////
// Events //
////////////

// @notice Notifies of a settings link update
@event
func settings_link_updated() {
}

@event
func settings_contract_created(
    contract_address: felt, registry_address: felt, version: felt, caller_address: felt
) {
}

/////////////////
// Constructor //
/////////////////

// @notice Constructor of Settings contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of the contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);

    // Emit event
    let (contract_address) = get_contract_address();
    let (caller_address) = get_caller_address();
    settings_contract_created.emit(contract_address, registry_address_, version_, caller_address);

    return ();
}

////////////////////
// View Functions //
////////////////////

// @notice Reads a stored settings link
// @returns link_len - Length of a link
// @returns link - List of link characters
@view
func get_settings_link{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
) -> (link_len: felt, link: felt*) {
    let (link_len, link) = StringLib.read_string(type=SETTINGS_LINK_TYPE, id=LINK_ID);
    return (link_len, link);
}

////////////////////////
// External Functions //
////////////////////////

// @notice Update settings link
// @param link_len - Length of the link
// @param link - List of link characters
@external
func update_settings_link{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    link_len: felt, link: felt*
) {
    // 1. Verify authority
    with_attr error_message("Settings: caller not authorized to manage settings") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_master_admin_or_authority(registry, version, ManageSettings_ACTION);
    }

    // 2. Remove existing link
    StringLib.remove_existing_string(type=SETTINGS_LINK_TYPE, id=LINK_ID);

    // 3. Save new link
    StringLib.save_string(
        type=SETTINGS_LINK_TYPE, 
        id=LINK_ID,
        string_len=link_len,
        string=link
    );

    // 4. Emit event
    settings_link_updated.emit();

    return ();
}