%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math_cmp import is_le
from contracts.Constants import Hightide_INDEX, Market_INDEX, TradingStats_INDEX
from contracts.DataTypes import HighTideFactors, HighTideMetaData, Market, TradingSeason
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHighTide import IHighTide
from contracts.interfaces.IMarkets import IMarkets
from contracts.interfaces.ITradingStats import ITradingStats
from contracts.libraries.CommonLibrary import (
    CommonLib,
    get_contract_version,
    get_registry_address,
    set_contract_version,
    set_registry_address,
)
from contracts.Math_64x61 import Math64x61_div, Math64x61_fromIntFelt

//#########
// Events #
//#########

// Event emitted whenever collateral is transferred from account by trading
@event
func high_tide_factors_set(season_id: felt, pair_id: felt, factors: HighTideFactors) {
}

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

//#####################
// External Functions #
//#####################

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
        assert is_expired = 1;
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

//#####################
// Internal Functions #
//#####################

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