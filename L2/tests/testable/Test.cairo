%lang starknet

%builtins pedersen range_check ecdsa

from starkware.starknet.common.syscalls import get_block_timestamp
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math_cmp import is_le

// //////////
// Storage //
// //////////

// @notice Stores the contract version
@storage_var
func timestamp() -> (res: felt) {
}

// @notice Stores the contract version
@storage_var
func test() -> (res: felt) {
}

// ///////
// View //
// ///////

@view
func return_timestamp{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (block_timestamp) = get_block_timestamp();
    return (block_timestamp,);
}

// ///////////
// External //
// ///////////

@external
func calc_abr{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(x: felt) -> (
    res: felt
) {
    alloc_locals;
    let (block_timestamp) = get_block_timestamp();
    let (last_call) = timestamp.read();

    let eight_hours = last_call + 28000;
    let is_eight_hours = is_le(eight_hours, block_timestamp);

    if (is_eight_hours == 0) {
        return (1,);

        // tempvar syscall_ptr = syscall_ptr
        // tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        // tempvar range_check_ptr = range_check_ptr
    } else {
        return (0,);
        // tempvar syscall_ptr = syscall_ptr
        // tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        // tempvar range_check_ptr = range_check_ptr
    }
}
