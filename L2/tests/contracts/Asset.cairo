%lang starknet
%builtins pedersen range_check
from starkware.cairo.common.cairo_builtins import HashBuiltin

@storage_var
func asset() -> (res: felt) {
}

@external
func set_asset_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(val: felt) {
    asset.write(val);
    return ();
}

@view
func get_asset_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (res) = asset.read();
    return (res,);
}
