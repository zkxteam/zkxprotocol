%lang starknet

from contracts.Constants import AccountRegistry_INDEX
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.UserBatches import calculate_no_of_batches, get_batch

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero, assert_nn, assert_le
from starkware.starknet.common.syscalls import get_caller_address

// //////////
// Storage //
// //////////

@storage_var
func index() -> (value: felt) {
}

@storage_var
func no_of_users_per_batch() -> (value: felt) {
}

@storage_var
func batches_fetched_for_index(index) -> (batches_fetched: felt) {
}

@storage_var
func no_of_batches_for_index(index) -> (no_of_batches: felt) {
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
    no_of_users_per_batch.write(5);
    return ();
}

// ///////
// View //
// ///////

// @notice Gets the current index
// @returns current_index
@view
func get_current_index{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    current_index: felt
) {
    let (current_index) = index.read();
    return (current_index,);
}

// @notice Gets the number of batches for an index
// @returns no_of_batches
@view
func get_no_of_batches{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    no_of_batches: felt
) {
    let (current_index) = index.read();
    let (no_of_batches) = no_of_batches_for_index.read(index=current_index);

    return (no_of_batches,);
}

// @notice Gets the number of users in a batch
// @returns no_of_users
@view
func get_no_of_users_per_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    ) -> (no_of_users: felt) {
    let (no_of_users) = no_of_users_per_batch.read();

    return (no_of_users,);
}

// ///////////
// External //
// ///////////

// @notice Function to increment the index and calculate the number of batches for the new index
@external
func begin_batch_calls{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> () {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get account Registry address
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    );

    // Get current index
    let (local current_index) = index.read();
    let (current_no_of_users_per_batch) = no_of_users_per_batch.read();

    let (no_of_batches) = calculate_no_of_batches(
        current_no_of_users_per_batch_=current_no_of_users_per_batch,
        account_registry_address_=account_registry_address,
    );

    // Set the number of users
    no_of_batches_for_index.write(index=current_index + 1, value=no_of_batches);

    index.write(current_index + 1);

    return ();
}

// @notice Function to get the current batch (reverts if it crosses the set number of batches)
// @returns users_list_len - Length of the user batch
// @returns users_list - Users batch
@external
func get_current_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    users_list_len: felt, users_list: felt*
) {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get account Registry address
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    );

    // Current Index
    let (current_index) = index.read();
    let (current_no_of_users_per_batch) = no_of_users_per_batch.read();
    let (batches_fetched) = batches_fetched_for_index.read(index=current_index);
    let (no_of_batches) = no_of_batches_for_index.read(index=current_index);

    if (no_of_batches == batches_fetched) {
        with_attr error_message("TestUserBatch: Invalid batch id") {
            assert 1 = 0;
        }
    }

    let (users_list_len, users_list) = get_batch(
        batch_id=batches_fetched,
        no_of_users_per_batch=current_no_of_users_per_batch,
        account_registry_address=account_registry_address,
    );

    batches_fetched_for_index.write(index=current_index, value=batches_fetched + 1);

    return (users_list_len, users_list);
}

// @notice Function to set the number of users in a batch
// @param new_no_of_users_per_batch
@external
func set_no_of_users_per_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_no_of_users_per_batch
) {
    no_of_users_per_batch.write(new_no_of_users_per_batch);
    return ();
}
