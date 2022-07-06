%lang starknet

from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import deploy
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.alloc import alloc
from contracts.libraries.Utils import verify_caller_authority
from contracts.Constants import (
    MasterAdmin_ACTION,
    AccountRegistry_INDEX
)

from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry

@storage_var
func pubkey_to_address(pubkey:felt) -> (address:felt):
end

@storage_var
func account_class_hash() -> (class_hash:felt):
end

@storage_var
func L1_ZKX_address() -> (address:felt):
end

@storage_var
func registry_address() -> (address:felt):
end

@storage_var
func version() -> (res:felt):
end

@storage_var
func salt() -> (res:felt):
end

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):

    assert_not_zero(registry_address_)
    assert_not_zero(version_)

    registry_address.write(registry_address_)
    version.write(version_)
    return()
end

@external
func deploy_account{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    public_key:felt):

    let (hash) = account_class_hash.read()
    let (current_salt)= salt.read()
    let (current_L1_ZKX_address)= L1_ZKX_address.read()
    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    let calldata:felt* = alloc()

    assert calldata[0] = public_key
    assert calldata[1] = current_registry_address
    assert calldata[2] = current_version
    assert calldata[3] = current_L1_ZKX_address

    let (deployed_address) = deploy(hash, current_salt, 4, calldata)

    pubkey_to_address.write(public_key, deployed_address)

    let (account_registry) = IAuthorizedRegistry.get_contract_address(
        contract_address=current_registry_address, index=AccountRegistry_INDEX, version=current_version)

    let (res) = IAccountRegistry.add_to_account_registry(account_registry, deployed_address)
    assert res = 1

    salt.write(current_salt+1)

    return()
end

@external
func set_account_class_hash{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    class_hash:felt):

    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)
    assert_not_zero(class_hash)

    account_class_hash.write(class_hash)

    return()
end

@external
func set_L1_ZKX_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address:felt):

    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)
    assert_not_zero(address)
    L1_ZKX_address.write(address)

    return()
end

@external
func set_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    new_version:felt):

    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)
    version.write(new_version)
    return()
end

@view
func get_account_class_hash{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (class_hash:felt):

    let (class_hash) = account_class_hash.read()
    return (class_hash)
end

@view
func get_pubkey_to_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    public_key:felt) -> (address:felt):

    let (address) = pubkey_to_address.read(public_key)
    return(address)
end

@view
func get_L1_ZKX_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (address:felt):

    let (current_L1_ZKX_address) = L1_ZKX_address.read()
    return(current_L1_ZKX_address)
end

@view
func get_registry_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (address:felt):

    let(current_registry_address)=registry_address.read()
    return (current_registry_address)
end

@view
func get_current_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (current_version:felt):

    let (current_version) = version.read()
    return (current_version)
end



