%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import deploy

from contracts.Constants import AccountRegistry_INDEX, MasterAdmin_ACTION
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.CommonLibrary import (
CommonLib, 
get_contract_version, 
get_registry_address, 
set_contract_version,
set_registry_address
)
from contracts.libraries.Utils import verify_caller_authority

//##########
// Events  #
//##########

// this event is emitted whenever the account contract class hash is changed by the admin
@event
func class_hash_changed(class_hash: felt) {
}

// this event is emitted whenever a new account is deployed
@event
func account_deployed(pubkey: felt, L1_address: felt, account_address: felt) {
}

// this event is emitted whenever the version for this contract is changed by the admin
@event
func version_changed(new_version: felt) {
}

//##########
// Storage #
//##########

// stores mapping from (pubkey, L1 address) -> (L2 address)
@storage_var
func pubkey_L1_to_address(pubkey: felt, L1_address: felt) -> (address: felt) {
}

// stores class hash of Account contract
@storage_var
func account_class_hash() -> (class_hash: felt) {
}

//##############
// Constructor #
//##############

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    return ();
}

//#################
// View Functions #
//#################

// @notice view function to get account class hash
// @return class_hash - class hash of the account contract
@view
func get_account_class_hash{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    class_hash: felt
) {
    let (class_hash) = account_class_hash.read();
    return (class_hash,);
}

// @notice view function to get address of contract that was deployed with public_key
// @param public_key - starkkey generated from users signature
// @param L1_address - L1 address of the user
// @return address - returns l2 account contract address
@view
func get_pubkey_L1_to_address{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    public_key: felt, L1_address: felt
) -> (address: felt) {
    let (address) = pubkey_L1_to_address.read(public_key, L1_address);
    return (address,);
}

//#####################
// External Functions #
//#####################

// @notice external function to deploy an account
// @param public_key - starkkey generated from users signature
// @param L1_address - L1 address of the user
@external
func deploy_account{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    public_key: felt, L1_address: felt
) {
    let (hash) = account_class_hash.read();
    let (current_registry_address) = CommonLib.get_registry_address();
    let (current_version) = CommonLib.get_contract_version();

    with_attr error_message("Class hash cannot be 0") {
        assert_not_zero(hash);
    }

    let (stored_deployed_address) = pubkey_L1_to_address.read(public_key, L1_address);

    // check we havent already deployed this combination of public key and L1 address
    with_attr error_message("Account already exists with given pubkey and L1 address") {
        assert stored_deployed_address = FALSE;
    }

    // prepare constructor calldata for deploy call
    let calldata: felt* = alloc();

    assert calldata[0] = public_key;
    assert calldata[1] = L1_address;
    assert calldata[2] = current_registry_address;
    assert calldata[3] = current_version;

    // using a constant value for salt means redeploying with same public_key would not override the account address
    // in any case we now check that re-deployment cannot happen with same (pubkey, L1 address) so salt does not matter
    // If 'deploy_from_zero' (5th arg) is 1, the contract address is not affected by the deployer's address
    // we make it so that only a change in the Account contract hash or constructor calldata will lead to change in contract
    // address deployed
    let (deployed_address) = deploy(hash, 0, 4, calldata, 1);

    pubkey_L1_to_address.write(public_key, L1_address, deployed_address);

    // update account registry with new deployed contract address
    let (account_registry) = IAuthorizedRegistry.get_contract_address(
        contract_address=current_registry_address,
        index=AccountRegistry_INDEX,
        version=current_version,
    );

    // getting a return value from the add_to_account_registry function means that it was successful
    IAccountRegistry.add_to_account_registry(account_registry, deployed_address);

    account_deployed.emit(
        pubkey=public_key, L1_address=L1_address, account_address=deployed_address
    );
    return ();
}

// @notice external function to set class hash of the account contract - class hash can be obtained on making a declare transaction
// @param class_hash -  class hash of the account contract
@external
func set_account_class_hash{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    class_hash: felt
) {
    let (current_registry_address) = CommonLib.get_registry_address();
    let (current_version) = CommonLib.get_contract_version();

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION);

    with_attr error_message("Class hash cannot be 0") {
        assert_not_zero(class_hash);
    }

    account_class_hash.write(class_hash);
    class_hash_changed.emit(class_hash=class_hash);

    return ();
}
