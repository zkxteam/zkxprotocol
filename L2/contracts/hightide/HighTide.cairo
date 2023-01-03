%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_nn, assert_not_zero, split_felt
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import (
    deploy,
    get_block_number,
    get_block_timestamp,
    get_caller_address,
)
from starkware.cairo.common.uint256 import (
    Uint256,
    uint256_add,
    uint256_lt,
    uint256_mul,
    uint256_unsigned_div_rem,
)

from contracts.Constants import (
    HIGHTIDE_ACTIVE,
    HIGHTIDE_INITIATED,
    HighTideCalc_INDEX,
    ManageHighTide_ACTION,
    Market_INDEX,
    SEASON_CREATED,
    SEASON_ENDED,
    SEASON_STARTED,
    Starkway_INDEX,
    TokenLister_ACTION,
)
from contracts.DataTypes import (
    Constants,
    HighTideMetaData,
    Market,
    Multipliers,
    RewardToken,
    TradingSeason,
)
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IERC20 import IERC20
from contracts.interfaces.IHighTideCalc import IHighTideCalc
from contracts.interfaces.ILiquidityPool import ILiquidityPool
from contracts.interfaces.IMarkets import IMarkets
from contracts.interfaces.IStarkway import IStarkway
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from contracts.libraries.Validation import assert_bool
from contracts.Math_64x61 import Math64x61_fromIntFelt, Math64x61_mul, Math64x61_toFelt

// /////////
// Events //
// /////////

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

// Event emitted whenever trading season is ended
@event
func trading_season_ended(caller: felt, season_id: felt) {
}

// Event is emitted whenever the liquidity pool contract class hash is changed
@event
func liquidity_pool_contract_class_hash_changed(class_hash: felt) {
}

// Event is emitted whenever a new liquidity pool contract is deployed
@event
func liquidity_pool_contract_deployed(hightide_id: felt, contract_address: felt) {
}

// Event is emitted when an hightide is initialized
@event
func hightide_initialized(caller: felt, hightide_id: felt) {
}

// Event is emitted when an hightide is activated
@event
func hightide_activated(caller: felt, hightide_id: felt) {
}

// Event is emitted when an hightide is assigned to a season
@event
func assigned_hightide_to_season(hightide_id: felt, season_id: felt) {
}

// Event emitted whenever trader's reward for a market is ditributed
@event
func distributed_trader_reward(
    season_id: felt, market_id: felt, trader_address: felt, l1_token_address: felt, reward: Uint256
) {
}

// //////////
// Storage //
// //////////

// Stores the previous trading season id
@storage_var
func previous_trading_season() -> (season_id: felt) {
}

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

// Stores whether a market is listed under hightide in a season 
@storage_var
func market_under_hightide(season_id: felt, market_id: felt) -> (
    is_listed: felt
) {
}

// //////////////
// Constructor //
// //////////////

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

// ///////
// View //
// ///////

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
// @param season_id_ - id of the season
// @return trading_season - structure of trading season
@view
func get_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) -> (trading_season: TradingSeason) {
    verify_season_id_exists(season_id_);
    let (trading_season) = trading_season_by_id.read(season_id=season_id_);
    return (trading_season,);
}

// @notice View function to get hightide metadata for the supplied hightide id
// @param hightide_id_ - id of hightide
// @return hightide_metadata - structure of hightide metadata
@view
func get_hightide{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id_: felt
) -> (hightide_metadata: HighTideMetaData) {
    verify_hightide_id_exists(hightide_id_);
    let (hightide_metadata) = hightide_by_id.read(hightide_id=hightide_id_);
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
// @param hightide_id_ - id of hightide
// @return reward_tokens_list_len - length of reward tokens list
// @return reward_tokens_list - list of reward tokens
@view
func get_hightide_reward_tokens{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id_: felt
) -> (reward_tokens_list_len: felt, reward_tokens_list: RewardToken*) {
    alloc_locals;
    verify_hightide_id_exists(hightide_id_);
    let (reward_tokens: RewardToken*) = alloc();
    let (local reward_tokens_len) = reward_tokens_len_by_hightide.read(hightide_id_);
    populate_reward_tokens_recurse(hightide_id_, 0, reward_tokens_len, reward_tokens);
    return (reward_tokens_len, reward_tokens);
}

// @notice View function to get season's expiry state
// @param season_id_ - id of the season
// @return is_expired - returns FALSE if it is not expired else TRUE
@view
func get_season_expiry_state{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) -> (is_expired: felt) {
    alloc_locals;

    verify_season_id_exists(season_id_);
    // get current block timestamp
    let (local current_timestamp) = get_block_timestamp();

    // calculates current trading seasons end timestamp
    let (current_season: TradingSeason) = get_season(season_id_);
    let current_seasons_num_trading_days_in_secs = current_season.num_trading_days * 24 * 60 * 60;
    let current_seasons_end_timestamp = current_season.start_timestamp + current_seasons_num_trading_days_in_secs;

    let within_season = is_le(current_timestamp, current_seasons_end_timestamp);
    if (within_season == TRUE) {
        return (FALSE,);
    }
    return (TRUE,);
}

// @notice View function to get the list of hightide ids corresponding to the season id
// @param season_id_ - id of the season
// @return hightide_list_len - length of hightide list
// @return hightide_list - list of hightide ids
@view
func get_hightides_by_season_id{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) -> (hightide_list_len: felt, hightide_list: felt*) {
    alloc_locals;
    let (hightide_list: felt*) = alloc();
    let (local hightide_list_len) = hightide_by_season_id.read(season_id_, 0);
    populate_hightide_list_recurse(season_id_, 0, hightide_list_len, hightide_list);
    return (hightide_list_len, hightide_list);
}

// @notice View function to check whether a market is listed under hightide
// @param season_id_ - id of the season
// @param market_id_ - id of the market pair
// @return is_listed - returns True if yes, else it returns False
@view
func is_market_under_hightide{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, market_id_: felt
) -> (is_listed: felt) {
    let (is_listed) = market_under_hightide.read(season_id_, market_id_);
    return (is_listed,);
}

// ///////////
// External //
// ///////////

// @notice - This function is used for setting up trade season
// @param start_timestamp_ - start timestamp of the season
// @param num_trading_days_ - number of trading days
@external
func setup_trade_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    start_timestamp_: felt, num_trading_days_: felt
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
        start_block_number=0,
        start_timestamp=start_timestamp_,
        num_trading_days=num_trading_days_,
        status=SEASON_CREATED,
    );

    trading_season_by_id.write(season_id, trading_season);

    // Emit event
    let (caller) = get_caller_address();
    trading_season_set_up.emit(caller, trading_season);
    return ();
}

// @notice - This function is used for starting trade season
// @param season_id_ - id of the season
@external
func start_trade_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) {
    // Get previous season id
    let (previous_season_id) = previous_trading_season.read();

    if (previous_season_id != 0) {
        let (previous_season: TradingSeason) = get_season(previous_season_id);
        with_attr error_message("HighTide: Previous season should be ended to start new season") {
            assert previous_season.status = SEASON_ENDED;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    validate_season_to_start(season_id_);
    let (new_season: TradingSeason) = get_season(season_id_);

    // Get current block number
    let (current_block_number) = get_block_number();

    // Update start block number in trading season
    let trading_season: TradingSeason = TradingSeason(
        start_block_number=current_block_number,
        start_timestamp=new_season.start_timestamp,
        num_trading_days=new_season.num_trading_days,
        status=SEASON_STARTED,
    );

    trading_season_by_id.write(season_id_, trading_season);
    current_trading_season.write(season_id_);

    // Emit event
    let (caller) = get_caller_address();
    trading_season_started.emit(caller, season_id_);
    return ();
}

// @notice - This function is used for ending trade season
// @param season_id_ - id of the season
@external
func end_trade_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) {
    alloc_locals;
    let (local registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (season: TradingSeason) = get_season(season_id_);
    with_attr error_message("HighTide: Season's status should be started to end ") {
        assert season.status = SEASON_STARTED;
    }

    let (is_expired) = get_season_expiry_state(season_id_);
    with_attr error_message("HighTide: Trading season is still active") {
        assert is_expired = TRUE;
    }

    // Get HightideCalc contract address from Authorized Registry
    let (hightide_calc_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=HighTideCalc_INDEX, version=version
    );

    // Calculate hightide factors
    IHighTideCalc.calculate_high_tide_factors(
        contract_address=hightide_calc_address, season_id_=season_id_
    );

    // Calculate R (Funds flow)
    IHighTideCalc.calculate_funds_flow(
        contract_address=hightide_calc_address, season_id_=season_id_
    );

    // Update status in trading season
    let trading_season: TradingSeason = TradingSeason(
        start_block_number=season.start_block_number,
        start_timestamp=season.start_timestamp,
        num_trading_days=season.num_trading_days,
        status=SEASON_ENDED,
    );
    trading_season_by_id.write(season_id_, trading_season);

    previous_trading_season.write(season_id_);
    current_trading_season.write(0);

    // Emit event
    let (caller) = get_caller_address();
    trading_season_ended.emit(caller, season_id_);
    return ();
}

// @notice - This function is used for setting multipliers
// @param a_1_ - alpha1 value
// @param a_2_ - alpha2 value
// @param a_3_ - alpha3 value
// @param a_4_ - alpha4 value
@external
func set_multipliers{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    a_1_: felt, a_2_: felt, a_3_: felt, a_4_: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("HighTide: Unauthorized call to set multipliers") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }

    // Create Multipliers struct to store
    let multipliers: Multipliers = Multipliers(a_1=a_1_, a_2=a_2_, a_3=a_3_, a_4=a_4_);
    multipliers_to_calculate_reward.write(multipliers);

    // Emit event
    let (caller) = get_caller_address();
    multipliers_for_rewards_added.emit(caller, multipliers);
    return ();
}

// @notice - This function is used for setting constants
// @param a_ - a value
// @param b_ - b value
// @param c_ - c value
// @param z_ - z value
// @param e_ - e value
@external
func set_constants{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    a_: felt, b_: felt, c_: felt, z_: felt, e_: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("HighTide: Unauthorized call to set constants") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }

    // Create Constants struct to store
    let constants: Constants = Constants(a=a_, b=b_, c=c_, z=z_, e=e_);
    constants_to_calculate_trader_score.write(constants);

    // Emit event
    let (caller) = get_caller_address();
    constants_for_trader_score_added.emit(caller, constants);
    return ();
}

// @notice external function to set class hash of liquidity pool contract
// @param class_hash_ -  class hash of the liquidity pool contract
@external
func set_liquidity_pool_contract_class_hash{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(class_hash_: felt) {
    let (current_registry_address) = CommonLib.get_registry_address();
    let (current_version) = CommonLib.get_contract_version();

    verify_caller_authority(current_registry_address, current_version, ManageHighTide_ACTION);

    with_attr error_message("HighTide: Class hash cannot be 0") {
        assert_not_zero(class_hash_);
    }

    liquidity_pool_contract_class_hash.write(class_hash_);

    // Emit event
    liquidity_pool_contract_class_hash_changed.emit(class_hash=class_hash_);

    return ();
}

// @notice - This function is used to initialize high tide
// @param market_id_ - supported market pair
// @param season_id_ - preferred season
// @param token_lister_address_ - L2 address of token lister
// @param is_burnable_ - if 0 - return to token lister, 1 - burn tokens
// @param reward_tokens_list_len - no.of reward tokens for an hightide
// @param reward_tokens_list - array of tokens to be given as reward
@external
func initialize_high_tide{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt,
    season_id_: felt,
    token_lister_address_: felt,
    is_burnable_: felt,
    reward_tokens_list_len: felt,
    reward_tokens_list: RewardToken*,
) {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("HighTide: Unauthorized call to initialize hightide") {
        verify_caller_authority(registry, version, TokenLister_ACTION);
    }

    let (is_expired) = get_season_expiry_state(season_id_);

    with_attr error_message("HighTide: Trading season already ended") {
        assert is_expired = FALSE;
    }

    with_attr error_message("HighTide: Token lister address cannot be 0") {
        assert_not_zero(token_lister_address_);
    }

    // Get market contract address
    let (market_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get Market from the corresponding market id
    let (market: Market) = IMarkets.get_market(
        contract_address=market_contract_address, market_id_=market_id_
    );

    with_attr error_message("HighTide: Listed market pair does not exist") {
        assert_not_zero(market.asset);
    }

    with_attr error_message("HighTide: is_burnable value should be boolean") {
        assert_bool(is_burnable_);
    }

    let (curr_len) = hightides_array_len.read();
    local hightide_id = curr_len + 1;
    hightides_array_len.write(curr_len + 1);

    let (liquidity_pool_address) = deploy_liquidity_pool_contract(hightide_id);

    // Create hightide metadata structure
    let hightide: HighTideMetaData = HighTideMetaData(
        market_id=market_id_,
        status=HIGHTIDE_INITIATED,
        season_id=season_id_,
        token_lister_address=token_lister_address_,
        is_burnable=is_burnable_,
        liquidity_pool_address=liquidity_pool_address,
    );

    hightide_by_id.write(hightide_id, hightide);

    reward_tokens_len_by_hightide.write(hightide_id, reward_tokens_list_len);
    set_hightide_reward_tokens_recurse(hightide_id, 0, reward_tokens_list_len, reward_tokens_list);

    // Emit event
    let (caller) = get_caller_address();
    hightide_initialized.emit(caller=caller, hightide_id=hightide_id);

    return ();
}

// @notice - This function is used to activate high tide
// @param hightide_id_ - id of hightide
@external
func activate_high_tide{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id_: felt
) {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("HighTide: Unauthorized call to activate hightide") {
        verify_caller_authority(registry, version, TokenLister_ACTION);
    }

    verify_hightide_id_exists(hightide_id_);

    // Get Starkway contract address
    let (local starkway_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Starkway_INDEX, version=version
    );

    let (
        reward_tokens_list_len: felt, reward_tokens_list: RewardToken*
    ) = get_hightide_reward_tokens(hightide_id_);

    let (hightide_metadata: HighTideMetaData) = get_hightide(hightide_id_);

    with_attr error_message("HighTide: Hightide is already activated") {
        assert hightide_metadata.status = HIGHTIDE_INITIATED;
    }
    let (status) = check_activation_recurse(
        hightide_metadata.liquidity_pool_address,
        starkway_contract_address,
        0,
        reward_tokens_list_len,
        reward_tokens_list,
    );
    if (status == TRUE) {
        // Update hightide status to active
        let hightide: HighTideMetaData = HighTideMetaData(
            market_id=hightide_metadata.market_id,
            status=HIGHTIDE_ACTIVE,
            season_id=hightide_metadata.season_id,
            token_lister_address=hightide_metadata.token_lister_address,
            is_burnable=hightide_metadata.is_burnable,
            liquidity_pool_address=hightide_metadata.liquidity_pool_address,
        );

        hightide_by_id.write(hightide_id_, hightide);

        // Emit event
        let (caller) = get_caller_address();
        hightide_activated.emit(caller=caller, hightide_id=hightide_id_);

        assign_hightide_to_season(hightide_id_, hightide_metadata.season_id);
        
    } else {
        with_attr error_message("HighTide: Liquidity pool should be fully funded") {
            assert status = TRUE;
        }
        return ();
    }
    return ();
}

// @notice - This function is used to distribute rewards
// @param hightide_id_ - id of hightide
// @param trader_list_len - length of trader's list
// @param trader_list - list of trader's
@external
func distribute_rewards{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id_: felt, trader_list_len: felt, trader_list: felt*
) {
    alloc_locals;
    // To-do: Need to integrate signature infra for the authentication

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get HightideCalc contract address from Authorized Registry
    let (hightide_calc_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=HighTideCalc_INDEX, version=version
    );

    // Get percentage of funds transferred from liquidity pool to reward pool
    let (local hightide_metadata: HighTideMetaData) = get_hightide(hightide_id_);
    let (funds_flow_64x61) = IHighTideCalc.get_funds_flow_per_market(
        contract_address=hightide_calc_address,
        season_id_=hightide_metadata.season_id,
        market_id_=hightide_metadata.market_id,
    );

    // Get reward tokens associated with the hightide
    let (
        reward_tokens_list_len: felt, reward_tokens_list: RewardToken*
    ) = get_hightide_reward_tokens(hightide_id_);

    // Recursively distribute rewards to all active traders for the specified hightide
    distribute_rewards_recurse(
        hightide_metadata_=hightide_metadata,
        funds_flow_64x61_=funds_flow_64x61,
        hightide_calc_address_=hightide_calc_address,
        trader_list_len=trader_list_len,
        trader_list=trader_list,
        reward_tokens_list_len=reward_tokens_list_len,
        reward_tokens_list=reward_tokens_list,
    );

    ILiquidityPool.perform_return_or_burn(
        contract_address=hightide_metadata.liquidity_pool_address
    );

    return ();
}

// ///////////
// Internal //
// ///////////

func verify_season_id_exists{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) {
    with_attr error_message("HighTide: Trading season id existence mismatch") {
        assert_lt(0, season_id_);
        let (seasons_len) = seasons_array_len.read();
        assert_le(season_id_, seasons_len);
    }
    return ();
}

func verify_hightide_id_exists{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id_: felt
) {
    with_attr error_message("HighTide: Hightide id existence mismatch") {
        assert_lt(0, hightide_id_);
        let (hightide_len) = hightides_array_len.read();
        assert_le(hightide_id_, hightide_len);
    }
    return ();
}

func validate_season_to_start{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) {
    alloc_locals;

    // get current block timestamp
    let (current_timestamp) = get_block_timestamp();

    // get current season id
    let (current_season_id) = current_trading_season.read();
    if (current_season_id == 0) {
        return ();
    }

    let (is_expired) = get_season_expiry_state(current_season_id);
    with_attr error_message("HighTide: Current trading season is still active") {
        assert is_expired = TRUE;
    }

    verify_season_id_exists(season_id_);
    // calculates new trading seasons end timestamp
    let (new_season: TradingSeason) = get_season(season_id_);
    let new_seasons_num_trading_days_in_secs = new_season.num_trading_days * 24 * 60 * 60;
    let new_seasons_end_timestamp = new_season.start_timestamp + new_seasons_num_trading_days_in_secs;

    with_attr error_message("HighTide: Invalid Timestamp") {
        assert_le(new_season.start_timestamp, current_timestamp);
    }

    with_attr error_message("HighTide: Invalid Timestamp") {
        assert_lt(current_timestamp, new_seasons_end_timestamp);
    }
    return ();
}

func set_hightide_reward_tokens_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    hightide_id_: felt, index_: felt, reward_tokens_list_len: felt, reward_tokens_list: RewardToken*
) {
    if (index_ == reward_tokens_list_len) {
        return ();
    }

    // Create reward token structure
    let reward_token: RewardToken = RewardToken(
        token_id=[reward_tokens_list].token_id, no_of_tokens=[reward_tokens_list].no_of_tokens
    );

    hightide_rewards_by_id.write(hightide_id_, index_, reward_token);
    return set_hightide_reward_tokens_recurse(
        hightide_id_, index_ + 1, reward_tokens_list_len, reward_tokens_list + RewardToken.SIZE
    );
}

func deploy_liquidity_pool_contract{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(hightide_id_: felt) -> (deployed_address: felt) {
    let (hightide_metadata) = get_hightide(hightide_id_);
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

    assert calldata[0] = hightide_id_;
    assert calldata[1] = current_registry_address;
    assert calldata[2] = current_version;

    let (deployed_address) = deploy(hash, 0, 3, calldata, 1);

    // Emit event
    liquidity_pool_contract_deployed.emit(
        hightide_id=hightide_id_, contract_address=deployed_address
    );

    return (deployed_address=deployed_address);
}

func populate_reward_tokens_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    hightide_id_: felt, index_: felt, reward_tokens_list_len: felt, reward_tokens_list: RewardToken*
) {
    if (index_ == reward_tokens_list_len) {
        return ();
    }

    let reward_token: RewardToken = hightide_rewards_by_id.read(hightide_id_, index_);
    assert reward_tokens_list[index_] = reward_token;
    return populate_reward_tokens_recurse(
        hightide_id_, index_ + 1, reward_tokens_list_len, reward_tokens_list
    );
}

func check_activation_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    liquidity_pool_address_: felt,
    starkway_contract_address_: felt,
    iterator_: felt,
    reward_tokens_list_len: felt,
    reward_tokens_list: RewardToken*,
) -> (status: felt) {
    alloc_locals;
    if (iterator_ == reward_tokens_list_len) {
        return (TRUE,);
    }

    let (
        contract_address_list_len: felt, contract_address_list: felt*
    ) = IStarkway.get_whitelisted_token_addresses(
        contract_address=starkway_contract_address_, token_id=[reward_tokens_list].token_id
    );

    local balance_Uint256: Uint256;
    let (native_token_l2_address: felt) = IStarkway.get_native_token_address(
        contract_address=starkway_contract_address_, token_id=[reward_tokens_list].token_id
    );

    if (native_token_l2_address != 0) {
        let current_balance_Uint256: Uint256 = IERC20.balanceOf(
            native_token_l2_address, liquidity_pool_address_
        );
        assert balance_Uint256 = current_balance_Uint256;
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        assert balance_Uint256 = cast((low=0, high=0), Uint256);
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    let (token_balance_Uint256) = verify_token_balance_recurse(
        liquidity_pool_address_,
        balance_Uint256,
        0,
        contract_address_list_len,
        contract_address_list,
    );
    let (result) = uint256_lt(token_balance_Uint256, [reward_tokens_list].no_of_tokens);
    if (result == TRUE) {
        return (FALSE,);
    }

    return check_activation_recurse(
        liquidity_pool_address_,
        starkway_contract_address_,
        iterator_ + 1,
        reward_tokens_list_len,
        reward_tokens_list + RewardToken.SIZE,
    );
}

func verify_token_balance_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    liquidity_pool_address_: felt,
    balance_Uint256_: Uint256,
    iterator_: felt,
    contract_address_list_len: felt,
    contract_address_list: felt*,
) -> (token_balance_Uint256: Uint256) {
    if (iterator_ == contract_address_list_len) {
        return (balance_Uint256_,);
    }

    let current_balance_Uint256: Uint256 = IERC20.balanceOf(
        [contract_address_list], liquidity_pool_address_
    );

    let (new_balance_Uint256, carry) = uint256_add(balance_Uint256_, current_balance_Uint256);
    return verify_token_balance_recurse(
        liquidity_pool_address_,
        new_balance_Uint256,
        iterator_ + 1,
        contract_address_list_len,
        contract_address_list + 1,
    );
}

func assign_hightide_to_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id_: felt, season_id_: felt
) {
    let (is_expired) = get_season_expiry_state(season_id_);

    with_attr error_message("HighTide: Trading season already ended") {
        assert is_expired = FALSE;
    }

    let (index) = hightide_by_season_id.read(season_id_, 0);
    hightide_by_season_id.write(season_id_, index + 1, hightide_id_);

    // 0th index always stores the no.of hightides corresponding to the season
    hightide_by_season_id.write(season_id_, 0, index + 1);

    // Emit event
    assigned_hightide_to_season.emit(hightide_id=hightide_id_, season_id=season_id_);

    return ();
}

func populate_hightide_list_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(season_id_: felt, index_: felt, hightide_list_len: felt, hightide_list: felt*) {
    if (index_ == hightide_list_len) {
        return ();
    }

    let (hightide_id) = hightide_by_season_id.read(season_id_, index_ + 1);
    assert hightide_list[index_] = hightide_id;
    return populate_hightide_list_recurse(season_id_, index_ + 1, hightide_list_len, hightide_list);
}

func distribute_rewards_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_metadata_: HighTideMetaData,
    funds_flow_64x61_: felt,
    hightide_calc_address_: felt,
    trader_list_len: felt,
    trader_list: felt*,
    reward_tokens_list_len: felt,
    reward_tokens_list: RewardToken*,
) {
    if (trader_list_len == 0) {
        return ();
    }

    // Get trader's score (w) per market
    let (trader_score_64x61) = IHighTideCalc.get_trader_score_per_market(
        contract_address=hightide_calc_address_,
        season_id_=hightide_metadata_.season_id,
        market_id_=hightide_metadata_.market_id,
        trader_address_=[trader_list],
    );

    // Calculate individual reward (r) = R (funds flow) * w (trader's score)
    let (individual_reward_64x61) = Math64x61_mul(funds_flow_64x61_, trader_score_64x61);

    // Send reward from all the listed reward tokens of hightide
    distribute_rewards_per_trader_recurse(
        hightide_metadata_=hightide_metadata_,
        trader_address_=[trader_list],
        individual_reward_64x61_=individual_reward_64x61,
        reward_tokens_list_len=reward_tokens_list_len,
        reward_tokens_list=reward_tokens_list,
    );

    // Iterate over next trader to distribute reward
    return distribute_rewards_recurse(
        hightide_metadata_=hightide_metadata_,
        funds_flow_64x61_=funds_flow_64x61_,
        hightide_calc_address_=hightide_calc_address_,
        trader_list_len=trader_list_len - 1,
        trader_list=trader_list + 1,
        reward_tokens_list_len=reward_tokens_list_len,
        reward_tokens_list=reward_tokens_list,
    );
}

func distribute_rewards_per_trader_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    hightide_metadata_: HighTideMetaData,
    trader_address_: felt,
    individual_reward_64x61_: felt,
    reward_tokens_list_len: felt,
    reward_tokens_list: RewardToken*,
) {
    if (reward_tokens_list_len == 0) {
        return ();
    }

    // Convert individual reward from 64x61 to Uint256 format
    // to convert, we will multiply and divide the reward which is in decimals with one followed by some zeros.
    // Here, we considered one followed by 18 zeros.
    // Ex: to convert 0.1234 -> ((0.1234) * (1000000000000000000))/ (1000000000000000000) -> we will convert numerator and denominator to Uint256 and then perform division
    let (quintillion_64x61: felt) = Math64x61_fromIntFelt(1000000000000000000);
    let (trader_reward_64x61: felt) = Math64x61_mul(individual_reward_64x61_, quintillion_64x61);

    // Convert 64x61 value to felt value
    let (trader_reward: felt) = Math64x61_toFelt(trader_reward_64x61);

    // Convert felt value to Uint256 value
    let (quintillion_high: felt, quintillion_low: felt) = split_felt(1000000000000000000);
    let quintillion_Uint256: Uint256 = Uint256(low=quintillion_low, high=quintillion_high);

    let (reward_high: felt, reward_low: felt) = split_felt(trader_reward);
    let trader_reward_Uint256: Uint256 = Uint256(low=reward_low, high=reward_high);

    // Calculate the individual reward for the corresponding reward token
    let (individual_reward_Uint256, carry_Uint256) = uint256_mul(
        trader_reward_Uint256, [reward_tokens_list].no_of_tokens
    );

    // Get the reward to be transferred
    let (reward_Uint256, remainder_Uint256) = uint256_unsigned_div_rem(
        individual_reward_Uint256, quintillion_Uint256
    );

    // Transfer the calculated reward amount to the trader
    ILiquidityPool.distribute_reward_tokens(
        contract_address=hightide_metadata_.liquidity_pool_address,
        trader_address_=trader_address_,
        reward_amount_Uint256_=reward_Uint256,
        l1_token_address_=[reward_tokens_list].token_id,
    );

    // Emit event
    distributed_trader_reward.emit(
        season_id=hightide_metadata_.season_id,
        market_id=hightide_metadata_.market_id,
        trader_address=trader_address_,
        l1_token_address=[reward_tokens_list].token_id,
        reward=reward_Uint256,
    );

    // Iterate over the next reward token
    return distribute_rewards_per_trader_recurse(
        hightide_metadata_=hightide_metadata_,
        trader_address_=trader_address_,
        individual_reward_64x61_=individual_reward_64x61_,
        reward_tokens_list_len=reward_tokens_list_len - 1,
        reward_tokens_list=reward_tokens_list + RewardToken.SIZE,
    );
}
