%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin

from contracts.Math_64x61 import Math64x61_approx

@view
func calc{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    x: felt, decimals: felt
) -> (res: felt) {
    let (res) = Math64x61_approx(x, decimals);
    return (res,);
}
