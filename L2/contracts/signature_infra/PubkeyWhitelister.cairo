%lang starknet

from contracts.libraries.Utils import verify_caller_authority
from starkware.cairo.common.math import assert_not_zero
from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.Constants import MasterAdmin_ACTION

@storage_var
func pubkey_to_whitelist(pubkey : felt) -> (res : felt):
end

@storage_var
func registry_address() -> (address : felt):
end

@storage_var
func version() -> (res : felt):
end

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        registry_address_ : felt, version_ : felt):
    assert_not_zero(registry_address_)
    assert_not_zero(version_)

    registry_address.write(registry_address_)
    version.write(version_)
    return ()
end

@external
func set_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        new_version : felt):
    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)
    version.write(new_version)
    return ()
end

# @notice - function to whitelist a  public key - callable only by admin
@external
func whitelist_pubkey{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        pubkey : felt):
    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)

    pubkey_to_whitelist.write(pubkey, 1)
    return ()
end

# @notice - function to de-whitelist a  public key - callable only by admin
@external
func delist_pubkey{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        pubkey : felt):
    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)

    pubkey_to_whitelist.write(pubkey, 0)
    return ()
end

@view
func is_whitelisted{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        pubkey : felt) -> (res : felt):
    let (res) = pubkey_to_whitelist.read(pubkey)
    return (res)
end

@view
func get_registry_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        address : felt):
    let (current_registry_address) = registry_address.read()
    return (current_registry_address)
end

@view
func get_current_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        current_version : felt):
    let (current_version) = version.read()
    return (current_version)
end
