%lang starknet
%builtins pedersen range_check ecdsa

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_nn

# @notice Stores number of tokens each user holds
@storage_var
func user_tokens(address : felt) -> (number_of_tokens : felt):
end

# @notice Function to add user_tokens
# @param address - Address of the user
# @param action - Number of tokens to be added
@external
func add_user_tokens{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt, value : felt
):
    # Authorization needs to be added in the future
    let number_of_tokens : felt = user_tokens.read(address=address)
    user_tokens.write(address=address, value=number_of_tokens + value)
    return ()
end

# @notice Function to remove user_tokens
# @param address - Address of the user
# @param action - Number of tokens to be removed
@external
func remove_user_tokens{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt, value : felt
):
    # Authorization needs to be added in the future
    let number_of_tokens : felt = user_tokens.read(address=address)
    assert_nn(number_of_tokens - value)
    user_tokens.write(address=address, value=number_of_tokens - value)
    return ()
end

# @notice Function to get user_tokens
# @param address - Address of the user
# @return value - number of tokens user holds
@view
func get_user_tokens{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt
) -> (value : felt):
    let number_of_tokens : felt = user_tokens.read(address=address)
    return (value=number_of_tokens)
end
