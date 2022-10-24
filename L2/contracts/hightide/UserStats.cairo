%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address

from contracts.Constants import Hightide_INDEX, Trading_INDEX
from contracts.DataTypes import TradingSeason
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHighTide import IHighTide
from contracts.libraries.CommonLibrary import CommonLib
from contracts.Math_64x61 import Math64x61_add

// /////////
// Events //
// /////////

// //////////
// Storage //
// //////////

// Stores the fee charged on a trader for a pair in a season
@storage_var
func trader_fee_by_market(season_id: felt, pair_id: felt, trader_address: felt) -> (
    fee_64x61: felt
) {
}

// Stores total fee collected by the platform for a pair in a season
@storage_var
func total_fee_by_market(season_id: felt, pair_id: felt) -> (total_fee_64x61: felt) {
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

// @notice View function to get current season id
// @param season_id - id of the season
// @param pair_id - id of the pair
// @param trader_address - l2 address of the trader
// @return fee_64x61 - returns the fee charged on a trader for a pair in a season
@view
func get_trader_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt, pair_id: felt, trader_address: felt
) -> (fee_64x61: felt) {
    let (fee_64x61) = trader_fee_by_market.read(season_id, pair_id, trader_address);
    return (fee_64x61,);
}

// @notice View function to get the total fee collected by the platform for a pair in a season
// @param season_id - id of the season
// @param pair_id - id of the pair
// @return total_fee_64x61 - returns total fee collected by the platform for a pair in a season
@view
func get_total_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt, pair_id: felt
) -> (total_fee_64x61: felt) {
    let (total_fee_64x61) = total_fee_by_market.read(season_id, pair_id);
    return (total_fee_64x61,);
}

// ///////////
// External //
// ///////////

// @notice This function is called to record trader's fee
// @param pair_id - id of the pair
// @param trader_address - L2 address of the user
// @param fee_64x61 - fee charged on trader for the traded pair
@external
func record_trader_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    pair_id: felt, trader_address: felt, fee_64x61: felt
) {
    // This function checks whether season has ended
    let (season_id) = verify_season_existance();
    if (season_id == 0) {
        return ();
    }

    let (current_trader_fee_64x61) = trader_fee_by_market.read(season_id, pair_id, trader_address);
    let (updated_trader_fee_64x61) = Math64x61_add(current_trader_fee_64x61, fee_64x61);

    // Increment trader fee
    trader_fee_by_market.write(season_id, pair_id, trader_address, updated_trader_fee_64x61);

    return ();
}

// @notice This function is used to record total fee collected by the platform for a pair in a season
// @param pair_id - id of the pair
// @param fee_64x61 - total fee charged for the traded pair
@external
func record_total_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    pair_id: felt, fee_64x61: felt
) {
    // This function checks whether season has ended
    let (season_id) = verify_season_existance();
    if (season_id == 0) {
        return ();
    }

    let (current_fee_64x61) = total_fee_by_market.read(season_id, pair_id);
    let (updated_fee_64x61) = Math64x61_add(current_fee_64x61, fee_64x61);

    // Increment total fee
    total_fee_by_market.write(season_id, pair_id, updated_fee_64x61);

    return ();
}

// ///////////
// Internal //
// ///////////

func verify_season_existance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    season_id: felt
) {
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    );

    // Check that this call originated from Trading contract
    with_attr error_message("UserStats: Trading fee can be recorded only by Trading contract") {
        assert caller = trading_address;
    }

    // Get HightideAdmin address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get current season id from hightide
    let (season_id) = IHighTide.get_current_season_id(hightide_address);
    let invalid_season_id = is_le(season_id, 0);

    if (invalid_season_id == 1) {
        return (0,);
    }

    let (current_timestamp) = get_block_timestamp();

    // Get trading season data
    let (season: TradingSeason) = IHighTide.get_season(hightide_address, season_id);

    let current_seasons_num_trading_days_in_secs = season.num_trading_days * 24 * 60 * 60;
    let current_seasons_end_timestamp = season.start_timestamp + current_seasons_num_trading_days_in_secs;

    let within_season = is_le(current_timestamp, current_seasons_end_timestamp);
    if (within_season == 0) {
        return (0,);
    }
    return (season_id,);
}
