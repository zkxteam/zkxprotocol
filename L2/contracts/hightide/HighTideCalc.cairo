%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math_cmp import is_le
from contracts.Constants import (
    Hightide_INDEX,
    Market_INDEX,
    RewardsCalculation_INDEX,
    TradingStats_INDEX,
    UserStats_INDEX,
)
from contracts.DataTypes import (
    Constants,
    HighTideFactors,
    HighTideMetaData,
    Market,
    Multipliers,
    TradingSeason,
    VolumeMetaData,
)
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHighTide import IHighTide
from contracts.interfaces.IMarkets import IMarkets
from contracts.interfaces.IRewardsCalculation import IRewardsCalculation
from contracts.interfaces.ITradingStats import ITradingStats
from contracts.interfaces.IUserStats import IUserStats
from contracts.libraries.CommonLibrary import (
    CommonLib,
    get_contract_version,
    get_registry_address,
    set_contract_version,
    set_registry_address,
)
from contracts.Math_64x61 import (
    Math64x61_add,
    Math64x61_div,
    Math64x61_fromIntFelt,
    Math64x61_mul,
    Math64x61_pow,
    Math64x61_sub,
)

// ////////////
// Constants //
// ////////////

const NUM_1_64x61 = 2305843009213693952;

// /////////
// Events //
// /////////

// Event emitted whenever collateral is transferred from account by trading
@event
func high_tide_factors_set(season_id: felt, pair_id: felt, factors: HighTideFactors) {
}

// Event emitted whenever funds flow by market is calculated
@event
func funds_flow_by_market_set(season_id: felt, pair_id: felt, funds_flow: felt) {
}

// Event emitted whenever trader's score by market is calculated
@event
func trader_score_by_market_set(
    season_id: felt, pair_id: felt, trader_address: felt, trader_score: felt
) {
}

// //////////
// Storage //
// //////////

// Stores high tide factors for
@storage_var
func high_tide_factors(season_id: felt, pair_id: felt) -> (factors: HighTideFactors) {
}

// Stores the w values for a trader per pair in a season
// Here, w value is the numerator of trader score formula
@storage_var
func trader_w_value_by_market(season_id: felt, pair_id: felt, trader_address: felt) -> (
    w_value_64x61: felt
) {
}

// Stores the cumulative sum of w values for a pair in a season
// Here, total w value is the denominator of trader score formula
@storage_var
func total_w_value_by_market(season_id: felt, pair_id: felt) -> (total_w_value_64x61: felt) {
}

// Stores the trader score per pair in a season
@storage_var
func trader_score_by_market(season_id: felt, pair_id: felt, trader_address: felt) -> (
    trader_score_64x61: felt
) {
}

// Stores funds flow per pair in a season
@storage_var
func funds_flow_by_market(season_id: felt, pair_id: felt) -> (funds_flow_64x61: felt) {
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

// @notice view function to get the hightide factors of a pair
// @param season_id_ - Id of the season
// @param pair_id - Market Id of the pair
// @return res - A struct of type HighTideFactors
@view
func get_hightide_factors{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt
) -> (res: HighTideFactors) {
    let (factors) = high_tide_factors.read(season_id=season_id_, pair_id=pair_id_);
    return (res=factors);
}

// @notice view function to get the top stats of a season
// @param season_id_ - Id of the season
// @return max_trades_top_pair_64x61 - Value of the max trades in a season for a pair (in a day)
// @return number_of_traders_top_pair_64x61 - Value of the max number of traders in a season for a pair
// @return average_volume_top_pair_64x61 - Value of the average volume of the top pair in a season for a pair
@view
func find_top_stats{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) -> (
    max_trades_top_pair_64x61: felt,
    number_of_traders_top_pair_64x61: felt,
    average_volume_top_pair_64x61: felt,
) {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get HightideAdmin address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get trading stats contract from Authorized Registry
    let (trading_stats_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=TradingStats_INDEX, version=version
    );

    let (markets_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get all the tradable markets in the system
    let (pair_list_len: felt, pair_list: Market*) = IMarkets.get_markets_by_state(
        contract_address=markets_address, tradable_=1, archived_=0
    );

    return find_top_stats_recurse(
        season_id_=season_id_,
        hightide_address_=hightide_address,
        trading_stats_address_=trading_stats_address,
        pair_list_len_=pair_list_len,
        pair_list_=pair_list,
        max_trades_top_pair_64x61_=0,
        number_of_traders_top_pair_64x61_=0,
        average_volume_top_pair_64x61_=0,
    );
}

// @notice view function to get trader score of a pair
// @param season_id_ - Id of the season
// @param pair_id_ - Market Id of the pair
// @param trader_address_ - Address of the trader
// @return trader_score - returns traders score of a pair
@view
func get_trader_score_per_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, trader_address_: felt
) -> (trader_score: felt) {
    let (trader_score) = trader_score_by_market.read(season_id_, pair_id_, trader_address_);
    return (trader_score,);
}

// @notice view function to get funds flow of a pair
// @param season_id_ - Id of the season
// @param pair_id_ - Market Id of the pair
// @return funds_flow - returns the funds transferred from liquidity pool to reward pool for a pair
@view
func get_funds_flow_per_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt
) -> (funds_flow: felt) {
    let (funds_flow) = funds_flow_by_market.read(season_id_, pair_id_);
    return (funds_flow,);
}

// ///////////
// External //
// ///////////

// @notice external function to calculate the factors
// @param season_id_ - Season Id for which to calculate the factors of a pair
@external
func calculate_high_tide_factors{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get HightideAdmin address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get trading stats contract from Authorized Registry
    let (trading_stats_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=TradingStats_INDEX, version=version
    );

    // Get trading season data
    let (season: TradingSeason) = IHighTide.get_season(
        contract_address=hightide_address, season_id=season_id_
    );

    // Get the current day according to the season
    let (is_expired: felt) = IHighTide.get_season_expiry_state(
        contract_address=hightide_address, season_id=season_id_
    );

    with_attr error_message("HighTideCalc: Season still ongoing") {
        assert is_expired = TRUE;
    }

    // Get top stats across all the markets
    let (
        max_trades_top_pair_64x61: felt,
        number_of_traders_top_pair_64x61: felt,
        average_volume_top_pair_64x61: felt,
    ) = find_top_stats(season_id_=season_id_);

    // Find HighTide factors for highTide pairs
    let (pair_id_list_len: felt, pair_id_list: felt*) = IHighTide.get_hightides_by_season_id(
        contract_address=hightide_address, season_id=season_id_
    );

    // Recursively calculate the factors for each pair_id
    return calculate_high_tide_factors_recurse(
        pair_id_list_len=pair_id_list_len,
        pair_id_list=pair_id_list,
        trading_stats_address_=trading_stats_address,
        hightide_address_=hightide_address,
        season_id_=season_id_,
        average_volume_top_pair_64x61_=average_volume_top_pair_64x61,
        max_trades_top_pair_64x61_=max_trades_top_pair_64x61,
        number_of_traders_top_pair_64x61_=number_of_traders_top_pair_64x61,
        total_days_=season.num_trading_days,
    );
}

// @notice external function to calculate w
// @param season_id_ - Season Id for which to calculate the w for traders
// @param pair_id_ - Pair Id for which to calculate w
// @param trader_list_len - length of trader's list
// @param trader_list - list of trader's
@external
func calculate_w{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, trader_list_len: felt, trader_list: felt*
) {
    // To-do: Need to integrate signature infra for the authentication

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get HightideAdmin address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get user stats contract from Authorized Registry
    let (user_stats_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=UserStats_INDEX, version=version
    );

    // Get rewards calculation contract from Authorized Registry
    let (rewards_calculation_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=RewardsCalculation_INDEX, version=version
    );

    // Get trading season data
    let (season: TradingSeason) = IHighTide.get_season(
        contract_address=hightide_address, season_id=season_id_
    );

    // Get the current day according to the season
    let (is_expired: felt) = IHighTide.get_season_expiry_state(
        contract_address=hightide_address, season_id=season_id_
    );

    with_attr error_message("HighTideCalc: Season still ongoing") {
        assert is_expired = TRUE;
    }

    // Get Constants to calculate traders individual trader score
    let (constants: Constants) = IHighTide.get_constants(contract_address=hightide_address);

    // Recursively calculate w for each trader
    return calculate_w_recurse(
        season_id_=season_id_,
        pair_id_=pair_id_,
        constants_=constants,
        trader_list_len=trader_list_len,
        trader_list=trader_list,
        user_stats_address_=user_stats_address,
        rewards_calculation_address_=rewards_calculation_address,
    );
}

// @notice external function to calculate trader score
// @param season_id_ - Season Id for which to calculate the w for a trader per pair
// @param pair_id_ - Pair Id for which to calculate traders score
// @param trader_list_len - length of trader's list
// @param trader_list - list of trader's
@external
func calculate_trader_score{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, trader_list_len: felt, trader_list: felt*
) {
    // To-do: Need to integrate signature infra for the authentication

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get HightideAdmin address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get trading season data
    let (season: TradingSeason) = IHighTide.get_season(
        contract_address=hightide_address, season_id=season_id_
    );

    // Get the current day according to the season
    let (is_expired: felt) = IHighTide.get_season_expiry_state(
        contract_address=hightide_address, season_id=season_id_
    );

    with_attr error_message("HighTideCalc: Season still ongoing") {
        assert is_expired = TRUE;
    }

    // Recursively calculate trader score for pair
    return calculate_trader_score_recurse(
        season_id_=season_id_,
        pair_id_=pair_id_,
        trader_list_len=trader_list_len,
        trader_list=trader_list,
    );
}

// @notice external function to calculate the funds flowing from LP (Liquidity Pool) to RP (Rewards Pool)
// @param season_id_ - Season Id for which to calculate the flow of a pair
@external
func calculate_funds_flow{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) {
    alloc_locals;

    // To-do: Need to integrate signature infra for the authentication

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get Hightide contract address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get trading season data
    let (season: TradingSeason) = IHighTide.get_season(
        contract_address=hightide_address, season_id=season_id_
    );

    // Get the current day according to the season
    let (is_expired: felt) = IHighTide.get_season_expiry_state(
        contract_address=hightide_address, season_id=season_id_
    );

    with_attr error_message("HighTideCalc: Season still ongoing") {
        assert is_expired = TRUE;
    }

    // get hightide pairs
    let (hightide_list_len: felt, hightide_list: felt*) = IHighTide.get_hightides_by_season_id(
        contract_address=hightide_address, season_id=season_id_
    );

    // Get multipliers to calculate funds flow
    let (multipliers: Multipliers) = IHighTide.get_multipliers(contract_address=hightide_address);

    // Recursively calculate the flow for each pair_id
    return calculate_funds_flow_recurse(
        season_id_=season_id_,
        multipliers_=multipliers,
        hightide_address_=hightide_address,
        hightide_list_len=hightide_list_len,
        hightide_list=hightide_list,
    );
}

// ///////////
// Internal //
// ///////////

// @notice internal function to recursively calculate the factors
// @param pair_id_list_len - Length of the pair_id array
// @param pair_id_list - Array of pair_ids
// @param trading_stats_address_ - Address of the Trading stats contract
// @param hightide_address_ - Address of the HighTide contract
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param average_volume_top_pair_64x61_ - Average volume of the top pair in the season
// @param max_trades_top_pair_64x61_ - Max number of trades by the top pair in the season
// @param number_of_traders_top_pair_64x61_ - Number of unique traders for the top pair in the season
// @param total_days_ - Number of days the season is active
func calculate_high_tide_factors_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    pair_id_list_len: felt,
    pair_id_list: felt*,
    trading_stats_address_: felt,
    hightide_address_: felt,
    season_id_: felt,
    average_volume_top_pair_64x61_: felt,
    max_trades_top_pair_64x61_: felt,
    number_of_traders_top_pair_64x61_: felt,
    total_days_: felt,
) {
    alloc_locals;
    if (pair_id_list_len == 0) {
        return ();
    }

    let (highTideDetails: HighTideMetaData) = IHighTide.get_hightide(
        contract_address=hightide_address_, hightide_id=[pair_id_list]
    );

    let (x_1: felt) = calculate_x_1(
        season_id_=season_id_,
        pair_id_=highTideDetails.pair_id,
        trading_stats_address_=trading_stats_address_,
        average_volume_top_pair_64x61_=average_volume_top_pair_64x61_,
    );

    let (x_2: felt) = calculate_x_2(
        season_id_=season_id_,
        pair_id_=highTideDetails.pair_id,
        trading_stats_address_=trading_stats_address_,
        max_trades_top_pair_64x61_=max_trades_top_pair_64x61_,
    );

    let (x_3: felt) = calculate_x_3(
        season_id_=season_id_,
        pair_id_=highTideDetails.pair_id,
        total_days_=total_days_,
        trading_stats_address_=trading_stats_address_,
    );

    let (x_4: felt) = calculate_x_4(
        season_id_=season_id_,
        pair_id_=highTideDetails.pair_id,
        trading_stats_address_=trading_stats_address_,
        number_of_traders_top_pair_64x61_=number_of_traders_top_pair_64x61_,
    );

    let factors: HighTideFactors = HighTideFactors(x_1=x_1, x_2=x_2, x_3=x_3, x_4=x_4);

    // Write the calculated factors to storage
    high_tide_factors.write(season_id=season_id_, pair_id=highTideDetails.pair_id, value=factors);
    high_tide_factors_set.emit(
        season_id=season_id_, pair_id=highTideDetails.pair_id, factors=factors
    );

    return calculate_high_tide_factors_recurse(
        pair_id_list_len=pair_id_list_len - 1,
        pair_id_list=pair_id_list + 1,
        trading_stats_address_=trading_stats_address_,
        hightide_address_=hightide_address_,
        season_id_=season_id_,
        average_volume_top_pair_64x61_=average_volume_top_pair_64x61_,
        max_trades_top_pair_64x61_=max_trades_top_pair_64x61_,
        number_of_traders_top_pair_64x61_=number_of_traders_top_pair_64x61_,
        total_days_=total_days_,
    );
}

// @notice internal function to calculate x_1 for a pair
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param pair_id_- Pair Id for which to calculate x_1
// @param trading_stats_address_ - Address of the Trading stats contract
// @param average_volume_top_pair_64x61_ - Average volume of the top pair in the season
// @returns x_1 - x_1 value for the pair
func calculate_x_1{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    pair_id_: felt,
    trading_stats_address_: felt,
    average_volume_top_pair_64x61_: felt,
) -> (x_1: felt) {
    if (average_volume_top_pair_64x61_ == 0) {
        return (0,);
    }
    let (average_volume_pair_64x61: felt) = ITradingStats.get_average_order_volume(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=pair_id_
    );
    let (x_1: felt) = Math64x61_div(average_volume_pair_64x61, average_volume_top_pair_64x61_);

    return (x_1,);
}

// @notice internal function to calculate x_2 for a pair
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param pair_id_- Pair Id for which to calculate x_2
// @param trading_stats_address_ - Address of the Trading stats contract
// @param max_trades_top_pair_64x61_ - Max number of trades by the top pair in the season
// @returns x_2 - x_2 value for the pair
func calculate_x_2{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, trading_stats_address_: felt, max_trades_top_pair_64x61_: felt
) -> (x_2: felt) {
    if (max_trades_top_pair_64x61_ == 0) {
        return (0,);
    }
    let (max_trades_pair: felt) = ITradingStats.get_max_trades_in_day(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=pair_id_
    );

    let (max_trades_pair_64x61: felt) = Math64x61_fromIntFelt(max_trades_pair);

    let (x_2: felt) = Math64x61_div(max_trades_pair_64x61, max_trades_top_pair_64x61_);

    return (x_2,);
}

// @notice internal function to calculate x_3 for a pair
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param pair_id_- Pair Id for which to calculate x_2
// @param total_days_ - Number of days the season is active
// @param trading_stats_address_ - Address of the Trading stats contract
// @returns x_3 - x_3 value for the pair
func calculate_x_3{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, total_days_: felt, trading_stats_address_: felt
) -> (x_3: felt) {
    if (total_days_ == 0) {
        return (0,);
    }
    let (num_days_traded: felt) = ITradingStats.get_total_days_traded(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=pair_id_
    );

    let (num_days_traded_64x61: felt) = Math64x61_fromIntFelt(num_days_traded);
    let (total_days_64x61: felt) = Math64x61_fromIntFelt(total_days_);

    let (x3: felt) = Math64x61_div(num_days_traded_64x61, total_days_64x61);

    return (x3,);
}

// @notice internal function to calculate x_4 for a pair
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param pair_id_- Pair Id for which to calculate x_4
// @param trading_stats_address_ - Address of the Trading stats contract
// @param number_of_traders_top_pair_64x61_ - Number of unique traders for the top pair in the season
// @returns x_4 - x_4 value for the pair
func calculate_x_4{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    pair_id_: felt,
    trading_stats_address_: felt,
    number_of_traders_top_pair_64x61_: felt,
) -> (x_4: felt) {
    if (number_of_traders_top_pair_64x61_ == 0) {
        return (0,);
    }
    let (number_of_traders: felt) = ITradingStats.get_num_active_traders(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=pair_id_
    );

    let (number_of_traders_64x61: felt) = Math64x61_fromIntFelt(number_of_traders);

    let (x_4: felt) = Math64x61_div(number_of_traders_64x61, number_of_traders_top_pair_64x61_);

    return (x_4,);
}

// @notice internal function to recursively calculate w for each trader
// @param season_id_ - Season Id for which to calculate w for each trader of a pair
// @param pair_id_- Pair Id for which to calculate w
// @param constants_ - Constants used to calculate individual trader score
// @param trader_list_len - Length of the traders array
// @param trader_list - Array of traders
// @param user_stats_address_ - Address of the User stats contract
// @param rewards_calculation_address_ - Address of the rewards calculation contract
func calculate_w_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    pair_id_: felt,
    constants_: Constants,
    trader_list_len: felt,
    trader_list: felt*,
    user_stats_address_: felt,
    rewards_calculation_address_: felt,
) {
    if (trader_list_len == 0) {
        return ();
    }

    // Get xp value
    let (xp_value: felt) = IRewardsCalculation.get_user_xp_value(
        contract_address=rewards_calculation_address_,
        season_id_=season_id_,
        user_address_=[trader_list],
    );

    // Calculate w per market
    calculate_w_per_market(
        season_id_=season_id_,
        pair_id_=pair_id_,
        trader_address_=[trader_list],
        user_stats_address_=user_stats_address_,
        xp_value_=xp_value,
        constants_=constants_,
    );

    // Recursively call next trader to calculate w
    return calculate_w_recurse(
        season_id_=season_id_,
        pair_id_=pair_id_,
        constants_=constants_,
        trader_list_len=trader_list_len - 1,
        trader_list=trader_list + 1,
        user_stats_address_=user_stats_address_,
        rewards_calculation_address_=rewards_calculation_address_,
    );
}

// @notice internal function to recursively calculate w for each trader
// @param season_id_ - Season Id for which to calculate w for each trader of a pair
// @param pair_id_ - Pair Id for which to calculate w
// @param trader_address_ - Address of the trader
// @param user_stats_address_ - Address of the User stats contract
// @param xp_value_ - xp_value of a trader
// @param constants_ - Constants used to calculate individual trader score
func calculate_w_per_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    pair_id_: felt,
    trader_address_: felt,
    user_stats_address_: felt,
    xp_value_: felt,
    constants_: Constants,
) {
    alloc_locals;

    // Get fp value
    let (local fp_value: felt) = calculate_fp(
        season_id_=season_id_,
        pair_id_=pair_id_,
        trader_address_=trader_address_,
        user_stats_address_=user_stats_address_,
    );

    // Get ft value
    let (local ft_value: felt) = calculate_ft(
        season_id_=season_id_, pair_id_=pair_id_, user_stats_address_=user_stats_address_
    );

    // Get d value
    let (d_value: felt) = calculate_d(
        season_id_=season_id_,
        pair_id_=pair_id_,
        trader_address_=trader_address_,
        user_stats_address_=user_stats_address_,
    );

    // Get p value
    let (p_value: felt) = calculate_p(
        season_id_=season_id_,
        pair_id_=pair_id_,
        trader_address_=trader_address_,
        user_stats_address_=user_stats_address_,
    );

    // Calculate w value
    let (w_value_64x61: felt) = calculate_w_value(
        fp_value_64x61_=fp_value,
        ft_value_64x61_=ft_value,
        d_value_64x61_=d_value,
        p_value_64x61_=p_value,
        xp_value_=xp_value_,
        constants_=constants_,
    );

    // Update w value for a pair corresponding to a trader
    trader_w_value_by_market.write(season_id_, pair_id_, trader_address_, w_value_64x61);

    // Update total w value for a pair
    let (current_w_value_64x61) = total_w_value_by_market.read(season_id_, pair_id_);
    let (new_w_value_64x61) = Math64x61_add(current_w_value_64x61, w_value_64x61);
    total_w_value_by_market.write(season_id_, pair_id_, new_w_value_64x61);
    return ();
}

// @notice internal function to calculate fp for a pair corresponding to a trader
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param pair_id_- Pair Id for which to calculate x_4
// @param trader_address_ - l2 address of the trader
// @param user_stats_address_ - Address of the User stats contract
// @return fp - returns trader's individual trading fees paid
func calculate_fp{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, trader_address_: felt, user_stats_address_: felt
) -> (fp_value: felt) {
    // Get trader's individual trading fees paid
    let (fee_64x61) = IUserStats.get_trader_fee(
        contract_address=user_stats_address_,
        season_id_=season_id_,
        pair_id_=pair_id_,
        trader_address_=trader_address_,
    );

    return (fee_64x61,);
}

// @notice internal function to calculate ft for a pair
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param pair_id_- Pair Id for which to calculate x_4
// @param user_stats_address_ - Address of the User stats contract
// @return ft - returns overall zkx platform trading fees
func calculate_ft{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, user_stats_address_: felt
) -> (ft_value: felt) {
    // Get overall zkx platform trading fees
    let (total_fee_64x61) = IUserStats.get_total_fee(
        contract_address=user_stats_address_, season_id_=season_id_, pair_id_=pair_id_
    );

    return (total_fee_64x61,);
}

// @notice internal function to calculate d for a pair corresponding to a trader
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param pair_id_- Pair Id for which to calculate x_4
// @param trader_address_ - l2 address of the trader
// @param user_stats_address_ - Address of the User stats contract
// @return d - returns trader's average open interest
func calculate_d{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, trader_address_: felt, user_stats_address_: felt
) -> (d: felt) {
    // Create a VolumeMetadata struct for open orders
    let volume_metadata_pair_open: VolumeMetaData = VolumeMetaData(
        season_id=season_id_, pair_id=pair_id_, order_type=0
    );

    // Create a VolumeMetadata struct for close orders
    let volume_metadata_pair_close: VolumeMetaData = VolumeMetaData(
        season_id=season_id_, pair_id=pair_id_, order_type=1
    );

    // Get the order volume for open orders
    let (
        current_num_orders_open: felt, current_total_volume_open_64x61: felt
    ) = IUserStats.get_trader_order_volume(
        contract_address=user_stats_address_,
        trader_address_=trader_address_,
        volume_type_=volume_metadata_pair_open,
    );

    // Get the order volume for close orders
    let (
        current_num_orders_close: felt, current_total_volume_close_64x61: felt
    ) = IUserStats.get_trader_order_volume(
        contract_address=user_stats_address_,
        trader_address_=trader_address_,
        volume_type_=volume_metadata_pair_close,
    );

    // check whether subtracting close order volume from open order volume is either positive or negative
    let is_negative = is_le(current_total_volume_open_64x61, current_total_volume_close_64x61);
    if (is_negative == TRUE) {
        return (0,);
    }

    // Find remaining open order volume after subtracting close order volume from it
    let (remaining_volume_open_64x61) = Math64x61_sub(
        current_total_volume_open_64x61, current_total_volume_close_64x61
    );

    // Find total orders by adding open and close orders
    let total_orders = current_num_orders_open + current_num_orders_close;

    if (total_orders == 0) {
        return (0,);
    }

    // Convert the total to 64x61 format
    let (total_orders_64x61) = Math64x61_fromIntFelt(total_orders);

    // Calculate average open interest
    let (d) = Math64x61_div(remaining_volume_open_64x61, total_orders_64x61);

    return (d,);
}

// @notice internal function to calculate p for a pair corresponding to a trader
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param pair_id_- Pair Id for which to calculate x_4
// @param trader_address_ - l2 address of the trader
// @param user_stats_address_ - Address of the User stats contract
// @return p - returns p value for a pair corresponding to a trader
func calculate_p{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, trader_address_: felt, user_stats_address_: felt
) -> (p: felt) {
    // Get pnl for a pair
    let (pnl_64x61) = IUserStats.get_trader_pnl(
        contract_address=user_stats_address_,
        season_id_=season_id_,
        pair_id_=pair_id_,
        trader_address_=trader_address_,
    );

    // Get margin amount for an order that is getting closed
    let (margin_amount_64x61) = IUserStats.get_trader_margin_amount(
        contract_address=user_stats_address_,
        season_id_=season_id_,
        pair_id_=pair_id_,
        trader_address_=trader_address_,
    );

    if (margin_amount_64x61 == 0) {
        return (0,);
    }

    // Calculate ratio of pnl to the margin
    let (p: felt) = Math64x61_div(pnl_64x61, margin_amount_64x61);

    return (p,);
}

// @notice internal function to calculate w for a pair corresponding to a trader
// @param fp_value_64x61_ - fp value for a pair corresponding to a trader
// @param ft_value_64x61_- ft value for a pair
// @param d_value_64x61_ - d value for a pair corresponding to a trader
// @param p_value_64x61_ - p value for a pair corresponding to a trader
// @param xp_value_ - xp value for a trader
// @param constants_ - constants used for calculating trader's score
// @return w - returns w value for a pair corresponding to a trader
func calculate_w_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    fp_value_64x61_: felt,
    ft_value_64x61_: felt,
    d_value_64x61_: felt,
    p_value_64x61_: felt,
    xp_value_: felt,
    constants_: Constants,
) -> (w_value_64x61: felt) {
    alloc_locals;

    let (updated_fp_value_64x61) = Math64x61_add(NUM_1_64x61, fp_value_64x61_);
    let (updated_ft_value_64x61) = Math64x61_add(NUM_1_64x61, ft_value_64x61_);
    let (fp_by_ft_64x61) = Math64x61_div(updated_fp_value_64x61, updated_ft_value_64x61);
    let (local fee_power_a) = Math64x61_pow(fp_by_ft_64x61, constants_.a);

    let (updated_d_value_64x61) = Math64x61_add(NUM_1_64x61, d_value_64x61_);
    let (d_power_b) = Math64x61_pow(updated_d_value_64x61, constants_.b);

    let (xp_value_64x61) = Math64x61_fromIntFelt(xp_value_);
    let (updated_xp_value) = max_of(constants_.z, xp_value_64x61);
    let (xp_power_c) = Math64x61_pow(updated_xp_value, constants_.c);

    let (updated_p_value_64x61) = Math64x61_add(NUM_1_64x61, p_value_64x61_);
    let (p_power_e) = Math64x61_pow(updated_p_value_64x61, constants_.e);

    let (temp_1_64x61) = Math64x61_mul(fee_power_a, d_power_b);
    let (temp_2_64x61) = Math64x61_mul(temp_1_64x61, xp_power_c);
    let (w_value_64x61) = Math64x61_mul(temp_2_64x61, p_power_e);

    return (w_value_64x61,);
}

// @notice internal function to find maximum of two numbers
// @param x_ - first number for the comparision
// @param y_ - second number for the comparision
// @return res - returns maximum of two numbers
func max_of{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    x_: felt, y_: felt
) -> (res: felt) {
    if (is_le(x_, y_) == 1) {
        return (y_,);
    }
    return (x_,);
}

// @notice internal function to recursively calculate trader score
// @param season_id_ - Season Id for which to calculate trader score for each trader of a pair
// @param pair_id_ - Pair Id for which to calculate traders score
// @param trader_list_len - Length of the traders array
// @param trader_list - Array of traders
func calculate_trader_score_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(season_id_: felt, pair_id_: felt, trader_list_len: felt, trader_list: felt*) {
    if (trader_list_len == 0) {
        return ();
    }

    // Calculate trader's score per market
    calculate_trader_score_per_market(
        season_id_=season_id_, pair_id_=pair_id_, trader_address_=[trader_list]
    );

    // Recursively calculate trader's score
    return calculate_trader_score_recurse(
        season_id_=season_id_,
        pair_id_=pair_id_,
        trader_list_len=trader_list_len - 1,
        trader_list=trader_list + 1,
    );
}

// @notice internal function to recursively calculate trader score
// @param season_id_ - Season Id for which to calculate trader score for each trader of a pair
// @param pair_id_ - Pair Id for which to calculate traders score
// @param trader_address_ - Address of the trader
func calculate_trader_score_per_market{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(season_id_: felt, pair_id_: felt, trader_address_: felt) {
    // Get w value for a pair corresponding to a trader
    let (w_value_64x61) = trader_w_value_by_market.read(season_id_, pair_id_, trader_address_);

    // Get total w value for a pair
    let (total_w_value_64x61) = total_w_value_by_market.read(season_id_, pair_id_);

    if (total_w_value_64x61 == 0) {
        return ();
    }

    let (trader_score_64x61) = Math64x61_div(w_value_64x61, total_w_value_64x61);

    // Update trader's score per market
    trader_score_by_market.write(season_id_, pair_id_, trader_address_, trader_score_64x61);

    // Emit event
    trader_score_by_market_set.emit(
        season_id=season_id_,
        pair_id=pair_id_,
        trader_address=trader_address_,
        trader_score=trader_score_64x61,
    );
    return ();
}

// @notice internal function to recursively calculate the top stats in a season
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param hightide_address_ - Address of the HighTide contract
// @param trading_stats_address_ - Address of the Trading stats contract
// @param pair_list_len - Length of the pair_id array
// @param pair_list - Array of pair_ids
// @param max_trades_top_pair_64x61_ - Current max number of trades by the top pair in the season for a market
// @param number_of_traders_top_pair_64x61_ - Current max number of unique traders in the season for a market
// @param average_volume_top_pair_64x61_ - Current max average volume in the season for a market
// @return max_trades_top_pair_64x61 - Max number of trades by the top pair in the season for a market
// @return number_of_traders_top_pair_64x61 - Max number of unique traders in the season for a market
// @return average_volume_top_pair_64x61 - Max average volume in the season for a market
func find_top_stats_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    hightide_address_: felt,
    trading_stats_address_: felt,
    pair_list_len_: felt,
    pair_list_: Market*,
    max_trades_top_pair_64x61_: felt,
    number_of_traders_top_pair_64x61_: felt,
    average_volume_top_pair_64x61_: felt,
) -> (
    max_trades_top_pair_64x61: felt,
    number_of_traders_top_pair_64x61: felt,
    average_volume_top_pair_64x61: felt,
) {
    alloc_locals;
    local current_max_trades_pair: felt;
    local current_top_number_of_traders: felt;
    local current_top_average_volume: felt;

    if (pair_list_len_ == 0) {
        return (
            max_trades_top_pair_64x61_,
            number_of_traders_top_pair_64x61_,
            average_volume_top_pair_64x61_,
        );
    }

    // Get max number of trades in a day for this highTide
    let (max_trades_pair: felt) = ITradingStats.get_max_trades_in_day(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=[pair_list_].id
    );

    // Convert the above stat to 64x61 format
    let (max_trades_64x61: felt) = Math64x61_fromIntFelt(max_trades_pair);

    // Get average volume for the pair in 64x61 format
    let (average_volume_64x61: felt) = ITradingStats.get_average_order_volume(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=[pair_list_].id
    );

    // Get number of activat traders for this pair
    let (number_of_traders: felt) = ITradingStats.get_num_active_traders(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=[pair_list_].id
    );

    // Convert the above stat to 64x61 format
    let (number_of_traders_64x61: felt) = Math64x61_fromIntFelt(number_of_traders);

    // Compare with our current largest stats
    let is_larger_volume = is_le(average_volume_top_pair_64x61_, average_volume_64x61);
    let is_larger_trades = is_le(max_trades_top_pair_64x61_, max_trades_64x61);
    let is_larger_traders = is_le(number_of_traders_top_pair_64x61_, number_of_traders_64x61);

    if (is_larger_volume == 1) {
        assert current_top_average_volume = average_volume_64x61;
    } else {
        assert current_top_average_volume = average_volume_top_pair_64x61_;
    }

    if (is_larger_trades == 1) {
        assert current_max_trades_pair = max_trades_64x61;
    } else {
        assert current_max_trades_pair = max_trades_top_pair_64x61_;
    }

    if (is_larger_traders == 1) {
        assert current_top_number_of_traders = number_of_traders_64x61;
    } else {
        assert current_top_number_of_traders = number_of_traders_top_pair_64x61_;
    }

    return find_top_stats_recurse(
        season_id_=season_id_,
        hightide_address_=hightide_address_,
        trading_stats_address_=trading_stats_address_,
        pair_list_len_=pair_list_len_ - 1,
        pair_list_=pair_list_ + Market.SIZE,
        max_trades_top_pair_64x61_=current_max_trades_pair,
        number_of_traders_top_pair_64x61_=current_top_number_of_traders,
        average_volume_top_pair_64x61_=current_top_average_volume,
    );
}

// @notice internal function to recursively calculate funds flow for each pair
// @param season_id_ - Season Id for which to calculate funds flow for each pair
// @param multipliers_ - Multipliers used to calculate funds flow
// @param hightide_address_ - Address of the HighTide contract
// @param hightide_list_len_, length of hightide market pair id's
// @param hightide_list_ - List of hightide market pair_ids
func calculate_funds_flow_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    multipliers_: Multipliers,
    hightide_address_: felt,
    hightide_list_len: felt,
    hightide_list: felt*,
) {
    alloc_locals;

    if (hightide_list_len == 0) {
        return ();
    }

    // Fetch hightide details
    let (hightide_details: HighTideMetaData) = IHighTide.get_hightide(
        contract_address=hightide_address_, hightide_id=[hightide_list]
    );

    // Get hightide factors corresponding to a pair
    let (factors: HighTideFactors) = high_tide_factors.read(
        season_id=season_id_, pair_id=hightide_details.pair_id
    );

    // Find cumulative sum of multipliers to the hightide factors
    let (x_1_times_a_1) = Math64x61_mul(factors.x_1, multipliers_.a_1);
    let (x_2_times_a_2) = Math64x61_mul(factors.x_2, multipliers_.a_2);
    let (x_3_times_a_3) = Math64x61_mul(factors.x_3, multipliers_.a_3);
    let (x_4_times_a_4) = Math64x61_mul(factors.x_4, multipliers_.a_4);

    let (temp_1_64x61) = Math64x61_add(x_1_times_a_1, x_2_times_a_2);
    let (temp_2_64x61) = Math64x61_add(temp_1_64x61, x_3_times_a_3);
    let (numerator_64x61) = Math64x61_add(temp_2_64x61, x_4_times_a_4);

    // Find sum of all multipliers
    let (temp_3_64x61) = Math64x61_add(multipliers_.a_1, multipliers_.a_2);
    let (temp_4_64x61) = Math64x61_add(temp_3_64x61, multipliers_.a_3);
    let (denominator_64x61) = Math64x61_add(temp_4_64x61, multipliers_.a_4);

    // if the denominator is 0, simply return
    if (denominator_64x61 == 0) {
        return ();
    }

    // Find percentage of funds to be transferred from LP to RP
    let (funds_flow_64x61) = Math64x61_div(numerator_64x61, denominator_64x61);

    // Update funds flow for a pair
    funds_flow_by_market.write(season_id_, hightide_details.pair_id, funds_flow_64x61);

    // Emit event
    funds_flow_by_market_set.emit(
        season_id=season_id_, pair_id=hightide_details.pair_id, funds_flow=funds_flow_64x61
    );

    // Recursively calculate the flow for each pair_id
    return calculate_funds_flow_recurse(
        season_id_=season_id_,
        multipliers_=multipliers_,
        hightide_address_=hightide_address_,
        hightide_list_len=hightide_list_len - 1,
        hightide_list=hightide_list + 1,
    );
}
