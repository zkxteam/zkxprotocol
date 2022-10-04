%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.starknet.common.syscalls import get_block_timestamp

from contracts.Constants import ManageHighTide_ACTION, Trading_INDEX
from contracts.DataTypes import TradingSeason
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority

//##########
// Storage #
//##########

// Stores the current trading season id
@storage_var
func current_trading_season() -> (season_id: felt) {
}

// Mapping between season id and trading season data
@storage_var
func trading_season_by_id(season_id: felt) -> (trading_season: TradingSeason) {
}

// Bool indicating if season id already exists
@storage_var
func season_id_exists(season_id: felt) -> (res: felt) {
}

//##############
// Constructor #
//##############

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

//#################
// View Functions #
//#################

// @notice View function to get current season id
// @returns season_id - Id of the season
@view
func get_current_season_id{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    season_id: felt
) {
    let (season_id) = current_trading_season.read();
    return (season_id,);
}

// @notice View function to get the trading season for the supplied season id
// @param season_id - id of the season
// @returns trading_season - structure of trading season
@view
func get_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt
) -> (trading_season: TradingSeason) {
    verify_season_id_exists(season_id, TRUE);
    let (trading_season) = trading_season_by_id.read(season_id=season_id);
    return (trading_season,);
}

//#####################
// External Functions #
//#####################

// @notice - This function is used for seeting up trade season
// @param num_trading_days - number of trading days
@external
func setup_trade_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt, num_trading_days: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("Caller is not authorized to setup trading") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }
    verify_season_id_exists(season_id, FALSE);
    
    let (current_timestamp) = get_block_timestamp();
    // Create Trading season struct to store
    let trading_season: TradingSeason = TradingSeason(
        start_timestamp=current_timestamp, num_trading_days=num_trading_days
    );

    trading_season_by_id.write(season_id, trading_season);
    current_trading_season.write(season_id);
    season_id_exists.write(season_id, TRUE);
    return ();
}

//#####################
// Internal functions #
//#####################

func verify_season_id_exists{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt, should_exist: felt
) {
    with_attr error_message("trading season id existence mismatch") {
        let (id_exists) = season_id_exists.read(season_id);
        assert id_exists = should_exist;
    }
    return ();
}