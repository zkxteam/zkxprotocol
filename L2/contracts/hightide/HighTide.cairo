%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address

from contracts.Constants import ManageHighTide_ACTION, Trading_INDEX
from contracts.DataTypes import Constants, Multipliers, TradingSeason
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority

//#########
// Events #
//#########

// Event emitted whenever mutipliers are set
@event
func multipliers_for_rewards_added(caller: felt, multipliers: Multipliers) {
}

// Event emitted whenever constants are set
@event
func constants_for_trader_score_added(caller: felt, constants: Constants) {
}

// Event emitted whenever trading season is set up
@event
func trading_season_set_up(caller: felt, trading_season: TradingSeason) {
}

// Event emitted whenever trading season is started
@event
func trading_season_started(caller: felt, season_id: felt) {
}

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

// Stores multipliers used to calculate total reward to be split between traders
@storage_var
func multipliers_to_calculate_reward() -> (multipliers: Multipliers) {
}

// Stores constants used to calculate individual trader score
@storage_var
func constants_to_calculate_trader_score() -> (constants: Constants) {
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

// @notice View function to get multipliers used to calculate total reward
// @returns multipliers - structure of Multipliers
@view
func get_multipliers{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    multipliers: Multipliers
) {
    let (multipliers) = multipliers_to_calculate_reward.read();
    return (multipliers,);
}

// @notice View function to get constants to calculate individual trader score
// @returns constants - structure of Constants
@view
func get_constants{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    constants: Constants
) {
    let (constants) = constants_to_calculate_trader_score.read();
    return (constants,);
}

//#####################
// External Functions #
//#####################

// @notice - This function is used for setting up trade season
// @param season_id - id of the season
// @param start_timestamp - start timestamp of the season
// @param num_trading_days - number of trading days
@external
func setup_trade_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt, start_timestamp: felt, num_trading_days: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("Caller is not authorized to setup trade season") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }
    verify_season_id_exists(season_id, FALSE);

    // Create Trading season struct to store
    let trading_season: TradingSeason = TradingSeason(
        start_timestamp=start_timestamp, num_trading_days=num_trading_days
    );

    trading_season_by_id.write(season_id, trading_season);
    season_id_exists.write(season_id, TRUE);

    // Emit event
    let (caller) = get_caller_address();
    trading_season_set_up.emit(caller, trading_season);
    return ();
}

// @notice - This function is used for starting trade season
// @param season_id - id of the season
@external
func start_trade_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("Caller is not authorized to start trade season") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }
    verify_season_id_exists(season_id, TRUE);

    current_trading_season.write(season_id);

    // Emit event
    let (caller) = get_caller_address();
    trading_season_started.emit(caller, season_id);
    return ();
}

// @notice - This function is used for setting multipliers
// @param a1 - alpha1 value
// @param a2 - alpha2 value
// @param a3 - alpha3 value
// @param a4 - alpha4 value
@external
func set_multipliers{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    a1: felt, a2: felt, a3: felt, a4: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("Caller is not authorized to set multipliers") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }

    // Create Multipliers struct to store
    let multipliers: Multipliers = Multipliers(a1=a1, a2=a2, a3=a3, a4=a4);
    multipliers_to_calculate_reward.write(multipliers);

    // Emit event
    let (caller) = get_caller_address();
    multipliers_for_rewards_added.emit(caller, multipliers);
    return ();
}

// @notice - This function is used for setting constants
// @param a - a value
// @param b - b value
// @param c - c value
// @param z - z value
// @param e - e value
@external
func set_constants{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    a: felt, b: felt, c: felt, z: felt, e: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("Caller is not authorized to set constants") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }

    // Create Constants struct to store
    let constants: Constants = Constants(a=a, b=b, c=c, z=z, e=e);
    constants_to_calculate_trader_score.write(constants);

    // Emit event
    let (caller) = get_caller_address();
    constants_for_trader_score_added.emit(caller, constants);
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
