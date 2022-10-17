%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_not_zero
from starkware.starknet.common.syscalls import (
    deploy,
    get_block_number,
    get_block_timestamp,
    get_caller_address,
)

from contracts.Constants import HIGHTIDE_INITIATED, ManageHighTide_ACTION, Trading_INDEX
from contracts.DataTypes import Constants, HighTideMetaData, Multipliers, RewardToken, TradingSeason
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_mul

// //////////
// Events //
// //////////

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

// this event is emitted whenever the liquidity pool contract class hash is changed
@event
func liquidity_pool_contract_class_hash_changed(class_hash: felt) {
}

// this event is emitted whenever a new liquidity pool contract is deployed
@event
func liquidity_pool_contract_deployed(hightide_id: felt, contract_address: felt) {
}

// ///////////
// Storage //
// ///////////

// Stores the current trading season id
@storage_var
func current_trading_season() -> (season_id: felt) {
}

// Mapping between season id and trading season data
@storage_var
func trading_season_by_id(season_id: felt) -> (trading_season: TradingSeason) {
}

// Stores multipliers used to calculate total reward to be split between traders
@storage_var
func multipliers_to_calculate_reward() -> (multipliers: Multipliers) {
}

// Stores constants used to calculate individual trader score
@storage_var
func constants_to_calculate_trader_score() -> (constants: Constants) {
}

// stores class hash of liquidity pool contract
@storage_var
func liquidity_pool_contract_class_hash() -> (class_hash: felt) {
}

// Length of seasons array
@storage_var
func seasons_array_len() -> (len: felt) {
}

// Length of hightide array
@storage_var
func hightides_array_len() -> (len: felt) {
}

// Mapping between hightide id and hightide metadata
@storage_var
func hightide_by_id(hightide_id: felt) -> (hightide: HighTideMetaData) {
}

// Mapping between hightide id and reward token data
@storage_var
func hightide_rewards_by_id(hightide_id: felt, index: felt) -> (reward_token: RewardToken) {
}

// Mapping between hightide id and reward tokens list length
@storage_var
func reward_tokens_len_by_hightide(hightide_id: felt) -> (len: felt) {
}

// Mapping between season id and hightide id
@storage_var
func hightide_by_season_id(season_id: felt, index: felt) -> (hightide_id: felt) {
}

// ///////////////
// Constructor //
// ///////////////

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

// ////////
// View //
// ////////

// @notice View function to get current season id
// @return season_id - Id of the season
@view
func get_current_season_id{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    season_id: felt
) {
    let (season_id) = current_trading_season.read();
    return (season_id,);
}

// @notice View function to get the trading season for the supplied season id
// @param season_id - id of the season
// @return trading_season - structure of trading season
@view
func get_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt
) -> (trading_season: TradingSeason) {
    verify_season_id_exists(season_id);
    let (trading_season) = trading_season_by_id.read(season_id=season_id);
    return (trading_season,);
}

// @notice View function to get hightide metadata for the supplied hightide id
// @param hightide_id - id of hightide
// @return hightide_metadata - structure of hightide metadata
@view
func get_hightide{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id: felt
) -> (hightide_metadata: HighTideMetaData) {
    verify_hightide_id_exists(hightide_id);
    let (hightide_metadata) = hightide_by_id.read(hightide_id=hightide_id);
    return (hightide_metadata,);
}

// @notice View function to get multipliers used to calculate total reward
// @return multipliers - structure of Multipliers
@view
func get_multipliers{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    multipliers: Multipliers
) {
    let (multipliers) = multipliers_to_calculate_reward.read();
    return (multipliers,);
}

// @notice View function to get constants to calculate individual trader score
// @return constants - structure of Constants
@view
func get_constants{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    constants: Constants
) {
    let (constants) = constants_to_calculate_trader_score.read();
    return (constants,);
}

// @notice View function to get list of reward tokens
// @param hightide_id - id of hightide
// @return reward_tokens_list_len - length of reward tokens list
// @return reward_tokens_list - list of reward tokens
@view
func get_hightide_reward_tokens{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id: felt
) -> (reward_tokens_list_len: felt, reward_tokens_list: RewardToken*) {
    alloc_locals;
    let (reward_tokens: RewardToken*) = alloc();
    let (reward_tokens_len) = reward_tokens_len_by_hightide.read(hightide_id);
    populate_reward_tokens(
        hightide_id, 0, reward_tokens_len, reward_tokens
    );
    return (reward_tokens_len, reward_tokens);
}

// ////////////
// External //
// ////////////

// @notice - This function is used for setting up trade season
// @param start_timestamp - start timestamp of the season
// @param num_trading_days - number of trading days
@external
func setup_trade_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    start_timestamp: felt, num_trading_days: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("HighTide: Unauthorized call to setup trade season") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }

    let (curr_len) = seasons_array_len.read();
    let season_id = curr_len + 1;
    seasons_array_len.write(curr_len + 1);

    // Create Trading season struct to store
    let trading_season: TradingSeason = TradingSeason(
        start_block_number=0, start_timestamp=start_timestamp, num_trading_days=num_trading_days
    );

    trading_season_by_id.write(season_id, trading_season);

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
    with_attr error_message("HighTide: Unauthorized call to start trade season") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }
    validate_season_to_start(season_id);

    let (new_season: TradingSeason) = get_season(season_id);

    // get current block number
    let (current_block_number) = get_block_number();

    // update start block number in trading season
    let trading_season: TradingSeason = TradingSeason(
        start_block_number=current_block_number,
        start_timestamp=new_season.start_timestamp,
        num_trading_days=new_season.num_trading_days,
    );

    trading_season_by_id.write(season_id, trading_season);
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
    with_attr error_message("HighTide: Unauthorized call to set multipliers") {
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
    with_attr error_message("HighTide: Unauthorized call to set constants") {
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

// @notice external function to set class hash of liquidity pool contract
// @param class_hash -  class hash of the liquidity pool contract
@external
func set_liquidity_pool_contract_class_hash{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(class_hash: felt) {
    let (current_registry_address) = CommonLib.get_registry_address();
    let (current_version) = CommonLib.get_contract_version();

    verify_caller_authority(current_registry_address, current_version, ManageHighTide_ACTION);

    with_attr error_message("HighTide: Class hash cannot be 0") {
        assert_not_zero(class_hash);
    }

    liquidity_pool_contract_class_hash.write(class_hash);
    liquidity_pool_contract_class_hash_changed.emit(class_hash=class_hash);

    return ();
}

// @notice - This function is used to initialize high tide
// @param pair_id - supported market pair
// @param season_id - preferred season
// @param is_burnable - if 0 - return to token lister, 1 - burn tokens
// @param reward_tokens_list_len - no.of reward tokens for an hightide
// @param reward_tokens_list - array of tokens to be given as reward
@external
func initialize_high_tide{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    pair_id: felt,
    season_id: felt,
    is_burnable: felt,
    reward_tokens_list_len: felt,
    reward_tokens_list: RewardToken*,
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("HighTide: Caller is not authorized to set constants") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }
    verify_season_id_exists(season_id);

    let (curr_len) = hightides_array_len.read();
    let hightide_id = curr_len + 1;
    hightides_array_len.write(curr_len + 1);

    let (liquidity_pool_address) = deploy_liquidity_pool_contract(hightide_id);

    // Create hightide metadata structure
    let hightide: HighTideMetaData = HighTideMetaData(
        pair_id=pair_id,
        status=HIGHTIDE_INITIATED,
        season_id=season_id,
        is_burnable=is_burnable,
        liquidity_pool_address=liquidity_pool_address,
    );

    let (curr_len) = hightides_array_len.read();
    let hightide_id = curr_len + 1;
    hightide_by_id.write(hightide_id, hightide);

    reward_tokens_len_by_hightide.write(hightide_id, reward_tokens_list_len);
    set_hightide_reward_tokens(hightide_id, 0, reward_tokens_list_len, reward_tokens_list);

    return ();
}

// ////////////
// Internal //
// ////////////

func verify_season_id_exists{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt
) {
    with_attr error_message("HighTide: Trading season id existence mismatch") {
        let (seasons_len) = seasons_array_len.read();
        assert_le(season_id, seasons_len);
    }
    return ();
}

func verify_hightide_id_exists{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id: felt
) {
    with_attr error_message("HighTide: Hightide id existence mismatch") {
        let (hightide_len) = hightides_array_len.read();
        assert_le(hightide_id, hightide_len);
    }
    return ();
}

func validate_season_to_start{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt
) {
    alloc_locals;

    verify_season_id_exists(season_id);

    // get current block timestamp
    let (current_timestamp) = get_block_timestamp();

    // calculates current trading seasons end timestamp
    let (local current_season_id) = get_current_season_id();
    let (current_season: TradingSeason) = get_season(current_season_id);
    let (current_seasons_num_trading_days_in_secs) = Math64x61_mul(
        current_season.num_trading_days, 24 * 60 * 60
    );
    let current_seasons_end_timestamp = current_season.start_timestamp + current_seasons_num_trading_days_in_secs;

    // calculates new trading seasons end timestamp
    let (new_season: TradingSeason) = get_season(season_id);
    let (new_seasons_num_trading_days_in_secs) = Math64x61_mul(
        new_season.num_trading_days, 24 * 60 * 60
    );
    let new_seasons_end_timestamp = new_season.start_timestamp + new_seasons_num_trading_days_in_secs;

    if (current_season_id != 0) {
        with_attr error_message("HighTide: Current trading season is still active") 
            assert_le(current_seasons_end_timestamp, current_timestamp);
        }
    } else {
        tempvar range_check_ptr = range_check_ptr;
    }

    with_attr error_message("HighTide: Invalid Timestamp") {
        assert_le(new_season.start_timestamp, current_timestamp);
    }

    with_attr error_message("HighTide: Invalid Timestamp") {
        assert_lt(current_timestamp, new_seasons_end_timestamp);
    }
    return ();
}

func set_hightide_reward_tokens{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id: felt, index: felt, reward_tokens_list_len: felt, reward_tokens_list: RewardToken*
) {
    if (index == reward_tokens_list_len) {
        return ();
    }

    // Create reward token structure
    let reward_token: RewardToken = RewardToken(
        token_id=[reward_tokens_list].token_id, no_of_tokens=[reward_tokens_list].no_of_tokens
    );

    hightide_rewards_by_id.write(hightide_id, index, reward_token);
    set_hightide_reward_tokens(
        hightide_id, index + 1, reward_tokens_list_len, reward_tokens_list + RewardToken.SIZE
    );
    return ();
}

func deploy_liquidity_pool_contract{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(hightide_id: felt) -> (deployed_address: felt) {
    let (hightide_metadata) = get_hightide(hightide_id);
    let (hash) = liquidity_pool_contract_class_hash.read();
    let (current_registry_address) = CommonLib.get_registry_address();
    let (current_version) = CommonLib.get_contract_version();

    with_attr error_message("HighTide: Class hash cannot be 0") {
        assert_not_zero(hash);
    }

    with_attr error_message(
            "HighTide: Liquidity pool contract already exists for the provided hightide") {
        assert hightide_metadata.liquidity_pool_address = FALSE;
    }

    // prepare constructor calldata for deploy call
    let calldata: felt* = alloc();

    assert calldata[0] = hightide_id;
    assert calldata[1] = current_registry_address;
    assert calldata[2] = current_version;

    let (deployed_address) = deploy(hash, 0, 3, calldata, 1);

    liquidity_pool_contract_deployed.emit(
        hightide_id=hightide_id, contract_address=deployed_address
    );

    return (deployed_address=deployed_address);
}

func populate_reward_tokens{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id: felt, index: felt, reward_tokens_list_len: felt, reward_tokens_list: RewardToken*
){
    if (index == reward_tokens_list_len) {
        return ();
    }

    let reward_token : RewardToken = hightide_rewards_by_id.read(hightide_id, index);
    assert reward_tokens_list[index] = reward_token;

    populate_reward_tokens(
        hightide_id, index + 1, reward_tokens_list_len, reward_tokens_list
    );
    return ();
}
