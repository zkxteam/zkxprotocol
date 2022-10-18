%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from contracts.libraries.CommonLibrary import CommonLib

/////////////
// Storage //
/////////////

// Stores hightide id of the corresponding liquidity pool contract
@storage_var
func hightide_id() -> (id: felt) {
}

// ///////////////
// Constructor //
// ///////////////

// @notice Constructor of the smart-contract
// @param high_tide_id - id of hightide
// @param registry_address Address of the AuthorizedRegistry contract
// @param version Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    high_tide_id: felt, registry_address: felt, version: felt
) {
    with_attr error_message("LiquidityPool: Hightide id cannot be 0") {
        assert_not_zero(high_tide_id);
    }

    hightide_id.write(high_tide_id);
    CommonLib.initialize(registry_address, version);
    return ();
}