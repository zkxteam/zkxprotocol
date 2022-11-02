%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import unsigned_div_rem, assert_le, assert_in_range, assert_lt
from starkware.cairo.common.math_cmp import is_nn, is_le
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHighTide import IHighTide
from contracts.interfaces.ITradingStats import ITradingStats
from contracts.Math_64x61 import Math64x61_div, Math64x61_fromIntFelt
from contracts.DataTypes import HighTideFactors, TradingSeason
from contracts.Constants import TradingStats_INDEX, Hightide_INDEX
from contracts.libraries.CommonLibrary import (
    CommonLib,
    get_contract_version,
    get_registry_address,
    set_contract_version,
    set_registry_address,
)

//##########
// Storage #
//##########

// Stores high tide factors for
@storage_var
func high_tide_factors(season_id: felt, pair_id: felt) -> (factors: HighTideFactors) {
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

// @notice view function to get the hightide factors of a pair
// @return res - A struct of type HighTideFactors
@view
func get_hightide_factors{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt
) -> (res: HighTideFactors) {
    let (factors) = high_tide_factors.read(season_id=season_id_, pair_id=pair_id_);
    return (res=factors);
}

@view
func find_top_stats{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) -> (
    max_trades_top_pair_64x61: felt,
    top_pair_number_of_traders: felt,
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

    let (hightide_list_len: felt, hightide_list: felt*) = IHighTide.get_hightides_by_season_id(
        contract_address=hightide_address, season_id=season_id_
    );

    return find_top_stats_recurse(
        hightide_address_=hightide_address,
        trading_stats_address_=trading_stats_address,
        hightide_list_len_=hightide_list_len,
        hightide_list_=hightide_list,
        max_trades_top_pair_64x61_=0,
        top_pair_number_of_traders_=0,
        average_volume_top_pair_64x61=0,
    );
}

//#####################
// External Functions #
//#####################

// @notice external function to calculate the factors
// @param pair_id_list_len - Length of the pair_id array
// @param pair_id_list - Array of pair_ids
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param top_pair_id_ - Top pair for the given season
@external
func calculate_high_tide_factors{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    pair_id_list_len: felt, pair_id_list: felt*, season_id_: felt, top_pair_id_: felt
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
    let (season: TradingSeason) = IHighTide.get_season(hightide_address, season_id_);

    // Get the current day according to the season
    let current_day = get_current_day(season.start_timestamp);

    let within_season = is_le(current_day, season.num_trading_days - 1);

    // If the season is over, calculate high tide factors
    if (within_season == 1) {
        return ();
    }

    let (
        top_pair_number_of_traders_64x61: felt,
        max_trades_top_pair_64x61: felt,
        average_volume_top_pair_64x61: felt,
    ) = find_top_stats(season_id_=season_id_);

    // Recursively calculate the factors for each pair_id
    return calculate_high_tide_factors_recurse(
        season_id_=season_id_,
        pair_id_list_len=pair_id_list_len,
        pair_id_list=pair_id_list,
        trading_stats_address_=trading_stats_address,
        season_id_=season_id_,
        average_volume_top_pair_64x61_=average_volume_top_pair_64x61,
        max_trades_top_pair_64x61_=max_trades_top_pair_64x61,
        top_pair_number_of_traders_64x61_=top_pair_number_of_traders_64x61,
        total_days_=season.num_trading_days,
    );
}

//#####################
// Internal Functions #
//#####################

// @notice internal function to recursively calculate the factors
// @param pair_id_list_len - Length of the pair_id array
// @param pair_id_list - Array of pair_ids
// @param trading_stats_address_ - Address of the Trading stats contract
// @param season_id_ - Season Id for which to calculate the factors of a pair
// @param average_volume_top_pair_64x61_ - Average volume of the top pair in the season
// @param max_trades_top_pair_64x61_ - Max number of trades by the top pair in the season
// @param top_pair_number_of_traders_64x61_ - Number of unique traders for the top pair in the season
// @param total_days_ - Number of days the season is active
func calculate_high_tide_factors_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    pair_id_list_len: felt,
    pair_id_list: felt*,
    trading_stats_address_: felt,
    season_id_: felt,
    average_volume_top_pair_64x61_: felt,
    max_trades_top_pair_64x61_: felt,
    top_pair_number_of_traders_64x61_: felt,
    total_days_: felt,
) {
    alloc_locals;
    if (pair_id_list_len == 0) {
        return ();
    }

    let (x_1: felt) = calculate_x_1(
        season_id_=season_id_,
        pair_id_=[pair_id_list],
        trading_stats_address_=trading_stats_address_,
        average_volume_top_pair_64x61_=average_volume_top_pair_64x61_,
    );

    let (x_2: felt) = calculate_x_2(
        season_id_=season_id_,
        pair_id_=[pair_id_list],
        trading_stats_address_=trading_stats_address_,
        max_trades_top_pair_64x61_=max_trades_top_pair_64x61_,
    );

    let (x_3: felt) = calculate_x_3(
        season_id_=season_id_,
        pair_id_=[pair_id_list],
        total_days_=total_days_,
        trading_stats_address_=trading_stats_address_,
    );

    let (x_4: felt) = calculate_x_4(
        season_id_=season_id_,
        pair_id_=[pair_id_list],
        trading_stats_address_=trading_stats_address_,
        top_pair_number_of_traders_64x61_=top_pair_number_of_traders_64x61_,
    );

    let factors: HighTideFactors = HighTideFactors(x_1=x_1, x_2=x_2, x_3=x_3, x_4=x_4);
    high_tide_factors.write(season_id=season_id_, pair_id=[pair_id_list], value=factors);

    return calculate_high_tide_factors_recurse(
        pair_id_list_len=pair_id_list_len - 1,
        pair_id_list=pair_id_list + 1,
        trading_stats_address_=trading_stats_address_,
        season_id_=season_id_,
        average_volume_top_pair_64x61_=average_volume_top_pair_64x61_,
        max_trades_top_pair_64x61_=max_trades_top_pair_64x61_,
        top_pair_number_of_traders_64x61_=top_pair_number_of_traders_64x61_,
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
) -> (res: felt) {
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
) -> (res: felt) {
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
// @param top_pair_number_of_traders_64x61_ - Number of unique traders for the top pair in the season
// @returns x_4 - x_4 value for the pair
func calculate_x_4{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    pair_id_: felt,
    trading_stats_address_: felt,
    top_pair_number_of_traders_64x61_: felt,
) -> (res: felt) {
    let (pair_number_of_traders: felt) = ITradingStats.get_num_active_traders(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=pair_id_
    );

    let (pair_number_of_traders_64x61: felt) = Math64x61_fromIntFelt(pair_number_of_traders);

    let (x_4: felt) = Math64x61_div(
        pair_number_of_traders_64x61, top_pair_number_of_traders_64x61_
    );

    return (x_4,);
}

func find_top_stats_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    hightide_address_: felt,
    trading_stats_address_: felt,
    hightide_list_len_: felt,
    hightide_list_: felt,
    max_trades_top_pair_64x61_: felt,
    top_pair_number_of_traders_: felt,
    average_volume_top_pair_64x61_: felt,
) -> (
    max_trades_top_pair_64x61: felt,
    top_pair_number_of_traders: felt,
    average_volume_top_pair_64x61: felt,
) {
    alloc_locals;
    local current_max_trades_pair: felt;
    local current_top_number_of_traders: felt;
    local current_top_average_volume: felt;

    if (hightide_list_len_ == 0) {
        return (
            max_trades_top_pair_64x61_, top_pair_number_of_traders_, average_volume_top_pair_64x61_
        );
    }

    let hightide_details: HighTideMetaData = IHighTide.get_hightide(
        contract_address=hightide_address_, hightide_id_=[hightide_list_]
    );

    let (max_trades_pair: felt) = ITradingStats.get_max_trades_in_day(
        contract_address=trading_stats_address_,
        season_id_=season_id_,
        pair_id_=hightide_details.pair_id,
    );

    let (max_trades_64x61: felt) = Math64x61_fromIntFelt(max_trades);

    let (average_volume_pair_64x61: felt) = ITradingStats.get_average_order_volume(
        contract_address=trading_stats_address_,
        season_id_=season_id_,
        pair_id_=hightide_details.pair_id,
    );

    let (pair_number_of_traders: felt) = ITradingStats.get_num_active_traders(
        contract_address=trading_stats_address_,
        season_id_=season_id_,
        pair_id_=hightide_details.pair_id,
    );

    let (pair_number_of_traders_64x61: felt) = Math64x61_fromIntFelt(pair_number_of_traders);

    let is_larger_volume = is_le(average_volume_top_pair_64x61_, average_volume_pair_64x61);
    let is_larger_trades = is_le(max_trades_top_pair_64x61_, max_trades_64x61);
    let is_larger_traders = is_le(top_pair_number_of_traders_, pair_number_of_traders);

    if (is_larger_volume == 1) {
        assert current_top_average_volume = average_volume_pair_64x61;
    } else {
        assert current_top_average_volume = average_volume_top_pair_64x61_;
    }

    if (is_larger_trades == 1) {
        assert current_max_trades_pair = max_trades_64x61;
    } else {
        assert current_max_trades_pair = max_trades_top_pair_64x61_;
    }

    if (is_larger_traders == 1) {
        assert current_top_number_of_traders = pair_number_of_traders;
    } else {
        assert current_top_number_of_traders = top_pair_number_of_traders_;
    }

    return find_top_stats_recurse(
        season_id_=season_id_,
        hightide_address_=hightide_address_,
        trading_stats_address_=trading_stats_address_,
        hightide_list_len_=hightide_list_len_ - 1,
        hightide_list_=hightide_list_ + 1,
        max_trades_top_pair_64x61_=current_max_trades_pair,
        top_pair_number_of_traders_=current_top_number_of_traders,
        average_volume_top_pair_64x61_=current_top_average_volume,
    );
}

// @dev - Returns current day of the season based on current timestamp
// if season has ended then it returns max number of trading days configured for the season
func get_current_day{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    start_timestamp: felt
) -> felt {
    alloc_locals;

    let (current_timestamp) = get_block_timestamp();
    local time_since_start = current_timestamp - start_timestamp;

    // Calculate current day = S/number of seconds in a day where S=time since start of season
    let (current_day, r) = unsigned_div_rem(time_since_start, 24 * 60 * 60);

    return current_day;
}
