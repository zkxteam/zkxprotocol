%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_lt, assert_nn

from contracts.Constants import ManageGovernanceToken_ACTION
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_add, Math64x61_sub

// /////////
// Events //
// /////////

// this event is emitted when tokens are added to a user's token count
@event
func tokens_added(user_address: felt, value_added: felt, prev_value: felt) {
}

// this event is emitted when tokens are removed from a user's token count
@event
func tokens_removed(user_address: felt, value_removed: felt, prev_value: felt) {
}

// //////////
// Storage //
// //////////

// Stores number of tokens each user holds
@storage_var
func user_tokens(address: felt) -> (number_of_tokens: felt) {
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

// ///////////
// External //
// ///////////

// @notice Function to add user_tokens
// @param address - Address of the user
// @param value - Number of tokens to be added
@external
func increment_governance_tokens{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address: felt, value: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    // Auth check
    with_attr error_message("FeeDiscount: Unauthorized call to manage governance tokens") {
        verify_caller_authority(registry, version, ManageGovernanceToken_ACTION);
    }

    with_attr error_message("FeeDiscount: Value must be > 0") {
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
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    // Auth check
    with_attr error_message("FeeDiscount: Unauthorized call to manage fee details") {
        verify_caller_authority(registry, version, ManageGovernanceToken_ACTION);
    }

    with_attr error_message("FeeDiscount: Value must be > 0") {
        assert_lt(0, value);
    }

    let number_of_tokens: felt = user_tokens.read(address=address);

    with_attr error_message("FeeDiscount: Insufficient balance") {
        assert_nn(number_of_tokens - value);
    }

    let (new_number_of_tokens) = Math64x61_sub(number_of_tokens, value);

    user_tokens.write(address=address, value=new_number_of_tokens);
    tokens_removed.emit(user_address=address, value_removed=value, prev_value=number_of_tokens);
    return ();
}
