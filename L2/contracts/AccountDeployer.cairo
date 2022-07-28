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

# stores mapping from (pubkey, L1 address) -> (L2 address)
@storage_var
func pubkey_L1_to_address(pubkey:felt, L1_address: felt) -> (address:felt):
end

# stores class hash of Account contract
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
    public_key:felt, L1_address: felt):

    let (hash) = account_class_hash.read()
    let (current_L1_ZKX_address)= L1_ZKX_address.read()
    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    assert_not_zero(hash)
    let (stored_deployed_address) = pubkey_L1_to_address.read(public_key, L1_address)

    # check we havent already deployed this combination of public key and L1 address
    with_attr error_message("Account already exists with given pubkey and L1 address"):
        assert stored_deployed_address = 0
    end

    # prepare constructor calldata for deploy call
    let calldata:felt* = alloc()

    assert calldata[0] = public_key
    assert calldata[1] = L1_address
    assert calldata[2] = current_registry_address
    assert calldata[3] = current_version
    assert calldata[4] = current_L1_ZKX_address

    # using a constant value for salt means redeploying with same public_key would not override the account address
    # in any case we now check that re-deployment cannot happen with same (pubkey, L1 address) so salt does not matter
    let (deployed_address) = deploy(hash, 0, 5, calldata) 

    pubkey_L1_to_address.write(public_key, L1_address, deployed_address)

    # update account registry with new deployed contract address
    let (account_registry) = IAuthorizedRegistry.get_contract_address(
        contract_address=current_registry_address, index=AccountRegistry_INDEX, version=current_version)

    let (res) = IAccountRegistry.add_to_account_registry(account_registry, deployed_address)
    assert res = 1

    return()
end

# set class hash of the account contract - class hash can be obtained on making a declare transaction
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

# get address of contract that was deployed with public_key
@view
func get_pubkey_L1_to_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    public_key:felt, L1_address: felt) -> (address:felt):

    let (address) = pubkey_L1_to_address.read(public_key, L1_address)
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



