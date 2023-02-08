%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from starkware.cairo.common.math import unsigned_div_rem

// ///////
// View //
// ///////

// Function to calculate the number of batches given the no_of_users_per_batch
// @param current_no_of_users_per_batch_ - Number of users in a batch
// @param account_registry_address_ - Account Registry address
@view
func calculate_no_of_batches{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    current_no_of_users_per_batch_: felt, account_registry_address_: felt
) -> (no_of_batches: felt) {
    alloc_locals;

    local no_of_batches;
    // Get the length of the account registry
    let (local current_registry_length) = IAccountRegistry.get_registry_len(
        contract_address=account_registry_address_
    );

    let (q, r) = unsigned_div_rem(current_registry_length, current_no_of_users_per_batch_);

    if (r == 0) {
        assert no_of_batches = q;
    } else {
        assert no_of_batches = q + 1;
    }

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
