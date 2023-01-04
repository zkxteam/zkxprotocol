%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.Math_64x61 import (
    Math64x61_ceil,
    Math64x61_div,
    Math64x61_fromIntFelt,
    Math64x61_toFelt,
)

// Function to calculate the number of batches given the no_of_users_per_batch
// @param current_no_of_users_per_batch_ - Number of users in a batch
// @param account_registry_address_ - Account Registry address
@view
func calculate_no_of_batches{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    current_no_of_users_per_batch_: felt, account_registry_address_: felt
) -> (no_of_batches: felt) {
    alloc_locals;
    // Get the length of the account registry
    let (local current_registry_length) = IAccountRegistry.get_registry_len(
        contract_address=account_registry_address_
    );

    // Convert the current_registry_length to 64x61 format
    let (current_registry_length_64x61) = Math64x61_fromIntFelt(current_registry_length);
    // Convert the current_no_of_users_per_batch_ to 64x61 format
    let (current_no_of_users_per_batch_64x61) = Math64x61_fromIntFelt(
        current_no_of_users_per_batch_
    );

    // Get the number of batches in 64x61 format
    let (no_of_batches_64x61) = Math64x61_div(
        current_registry_length_64x61, current_no_of_users_per_batch_64x61
    );
    // Remove the decimal part
    let (no_of_batches_ceil) = Math64x61_ceil(no_of_batches_64x61);
    // Convert the no_of_batches_64x61 to felt
    let (no_of_batches) = Math64x61_toFelt(no_of_batches_ceil);

    return (no_of_batches,);
}

// Function to fetch the corresponding batch given the batch id
// @param batch_id - Batch id of the batch
// @param no_of_users_per_batch - Number of users in a batch
// @param account_registry_address - Account Registry address
@view
func get_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    batch_id: felt, no_of_users_per_batch: felt, account_registry_address: felt
) -> (account_registry_len: felt, account_registry: felt*) {
    // Get the lower index of the batch
    let lower_limit: felt = batch_id * no_of_users_per_batch;
    // Get the upper index of the batch
    let upper_limit: felt = lower_limit + no_of_users_per_batch;

    // Fetch the required batch from AccountRegistry
    let (account_registry_len: felt, account_registry: felt*) = IAccountRegistry.get_batch(
        contract_address=account_registry_address,
        starting_index_=lower_limit,
        ending_index_=upper_limit,
    );

    return (account_registry_len, account_registry);
}
