%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin

from contracts.libraries.CommonLibrary import CommonLib

// /////////
// Events //
// /////////

// //////////
// Storage //
// //////////

// Stores the fee charged on a trader for a pair in a season
@storage_var
func trader_fee_by_market(season_id: felt, pair_id: felt, trader_address: felt) -> (fee: felt) {
}

// Stores total fee collected by the platform for a pair in a season
@storage_var
func total_fee_by_market(season_id: felt, pair_id: felt) -> (fee: felt) {
}

// //////////////
// Constructor //
// //////////////

// @notice Constructor of the smart-contract
// @param registry_address - Address of the AuthorizedRegistry contract
// @param version - Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address: felt, version: felt
) {
    CommonLib.initialize(registry_address, version);
    return ();
}

// ///////
// View //
// ///////

// ///////////
// External //
// ///////////

// ///////////
// Internal //
// ///////////
