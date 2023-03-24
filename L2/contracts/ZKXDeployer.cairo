%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import deploy

from contracts.Constants import MasterAdmin_ACTION
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority

// //////////
// Storage //
// //////////

// Stores the deployed addreses array
@storage_var
func deployed_addresses(index: felt) -> (contract_address: felt) {
}

// Stores the length of deployed addresses array
@storage_var
func deployed_addresses_len() -> (res: felt) {
}

// Stores the current nonce
@storage_var
func curr_nonce() -> (res: felt) {
}

// //////////////
// Constructor //
// //////////////

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

// ///////
// View //
// ///////

// @notice View function to return all the deployed contract addresses
// @returns array_len - Length of the last deployed array
// @returns array - Array of deployed contract addresses
@view
func populate_deployed_addresses{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    ) -> (array_len: felt, array: felt*) {
    let (array: felt*) = alloc();
    let (array_len: felt) = deployed_addresses_len.read();
    return populate_deployed_addresses_recurse(0, array, array_len);
}

// ///////////
// External //
// ///////////

// @notice External function to deploy_contracts
// @dev The hashes must be declared beforehand, the sequence of hashes must be handled by the deploy script
// @param hashes_len - Length of the hashes array
// @param hashes - Array of hashes to be deployed
@external
func deploy_contracts{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hashes_len: felt, hashes: felt*
) {
    let (current_registry_address) = CommonLib.get_registry_address();
    let (current_version) = CommonLib.get_contract_version();

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION);

    let calldata: felt* = alloc();

    assert calldata[0] = current_registry_address;
    assert calldata[1] = current_version;

    let (nonce) = curr_nonce.read();
    let (new_nonce) = deploy_contracts_recurse(hashes_len, hashes, calldata, 0, nonce);
    deployed_addresses_len.write(hashes_len);
    curr_nonce.write(new_nonce);

    return ();
}

// ///////////
// Internal //
// ///////////

// @notice Internal function to recursively deploy contracts
// @param hashes_len_ - Current length of the hashes array
// @param hashes_ - Array of hashes
// @param iterator_ - Iterator to index the array
// @param calldata_ - Calldata consisting of registry and version
// @param nonce_ - Current nonce
// @returns nonce_ - Final nonce
func deploy_contracts_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hashes_len_: felt, hashes_: felt*, calldata_: felt*, iterator_: felt, nonce_: felt
) -> (nonce: felt) {
    if (hashes_len_ == 0) {
        return (nonce_,);
    }

    let (deployed_address) = deploy([hashes_], nonce_, 2, calldata_, 1);
    deployed_addresses.write(index=iterator_, value=deployed_address);

    return deploy_contracts_recurse(
        hashes_len_ - 1, hashes_ + 1, calldata_, iterator_ + 1, nonce_ + 1
    );
}

// @notice Internal function to populate the array with deployed contract addresses
// @param array_len_ - Current length of the array
// @param array_ - Array being populated
// @param final_len_ - Final length of the array to tbe populated
// @returns array_len - Final length of the array
// @returns array - Array with the populated contract addresses
func populate_deployed_addresses_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(array_len_: felt, array_: felt*, final_len_: felt) -> (array_len: felt, array: felt*) {
    if (array_len_ == final_len_) {
        return (array_len_, array_);
    }

    let (deployed_address: felt) = deployed_addresses.read(index=array_len_);
    assert array_[array_len_] = deployed_address;
    return populate_deployed_addresses_recurse(array_len_ + 1, array_, final_len_);
}
