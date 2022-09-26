%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_lt, assert_nn, assert_not_zero

from contracts.Constants import ManageGovernanceToken_ACTION
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_add, Math64x61_sub

//##########
// Events  #
//##########

// this event is emitted when tokens are added to a user's token count
@event
func tokens_added(user_address: felt, value_added: felt, prev_value: felt) {
}

// this event is emitted when tokens are removed from a user's token count
@event
func tokens_removed(user_address: felt, value_removed: felt, prev_value: felt) {
}

//##########
// Storage #
//##########

// Stores the contract version
@storage_var
func contract_version() -> (version: felt) {
}

// Stores the address of Authorized Registry contract
@storage_var
func registry_address() -> (contract_address: felt) {
}

// Stores number of tokens each user holds
@storage_var
func user_tokens(address: felt) -> (number_of_tokens: felt) {
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
    with_attr error_message("Registry address and version cannot be 0") {
        assert_not_zero(registry_address_);
        assert_not_zero(version_);
    }

    registry_address.write(value=registry_address_);
    contract_version.write(value=version_);
    return ();
}

//#################
// View Functions #
//#################

// @notice Function to get user_tokens
// @param address - Address of the user
// @return value - number of tokens user holds
@view
func get_user_tokens{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address: felt
) -> (value: felt) {
    let number_of_tokens: felt = user_tokens.read(address=address);
    return (value=number_of_tokens);
}

//#####################
// External Functions #
//#####################

// @notice Function to add user_tokens
// @param address - Address of the user
// @param value - Number of tokens to be added
@external
func increment_governance_tokens{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address: felt, value: felt
) {
    let (registry) = registry_address.read();
    let (version) = contract_version.read();
    // Auth check
    with_attr error_message("Caller is not authorized to manage governance tokens") {
        verify_caller_authority(registry, version, ManageGovernanceToken_ACTION);
    }

    with_attr error_message("Value should be greater than 0") {
        assert_lt(0, value);
    }

    let number_of_tokens: felt = user_tokens.read(address=address);
    let (new_number_of_tokens) = Math64x61_add(number_of_tokens, value);

    user_tokens.write(address=address, value=new_number_of_tokens);
    tokens_added.emit(user_address=address, value_added=value, prev_value=number_of_tokens);
    return ();
}

// @notice Function to remove user_tokens
// @param address - Address of the user
// @param action - Number of tokens to be removed
@external
func decrement_governance_tokens{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address: felt, value: felt
) {
    let (registry) = registry_address.read();
    let (version) = contract_version.read();
    // Auth check
    with_attr error_message("Caller is not authorized to manage fee details") {
        verify_caller_authority(registry, version, ManageGovernanceToken_ACTION);
    }

    with_attr error_message("Value should be greater than 0") {
        assert_lt(0, value);
    }

    let number_of_tokens: felt = user_tokens.read(address=address);

    with_attr error_message("Cannot have number of tokens as negative after removal") {
        assert_nn(number_of_tokens - value);
    }

    let (new_number_of_tokens) = Math64x61_sub(number_of_tokens, value);

    user_tokens.write(address=address, value=new_number_of_tokens);
    tokens_removed.emit(user_address=address, value_removed=value, prev_value=number_of_tokens);
    return ();
}
