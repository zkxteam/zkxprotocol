%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin

from contracts.Math_64x61 import Math64x61_assert_le, Math64x61_is_le, Math64x61_round

@view
func calc{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    x: felt, precision: felt
) -> (res: felt) {
    let (res) = Math64x61_round(x, precision);
    return (res,);
}

@view
func math64x61_is_le{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    x: felt, y: felt, decimals: felt
) -> (res: felt) {
    let (res) = Math64x61_is_le(x, y, decimals);
    return (res,);
}

@view
func math64x61_assert_le{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    x: felt, y: felt, decimals: felt
) {
    Math64x61_assert_le(x, y, decimals);
    return ();
}
