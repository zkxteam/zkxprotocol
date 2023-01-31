%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin

from contracts.Math_64x61 import Math64x61_round

@view
func calc{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    x: felt, precision: felt
) -> (res: felt) {
    let (res) = Math64x61_round(x, precision);
    return (res,);
}
