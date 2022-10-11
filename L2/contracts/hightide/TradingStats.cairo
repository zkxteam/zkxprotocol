%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import unsigned_div_rem, assert_le, assert_in_range, assert_lt
from starkware.cairo.common.math_cmp import is_nn, is_le
from contracts.Constants import Hightide_INDEX, Trading_INDEX
from contracts.DataTypes import VolumeMetaData, OrderVolume, TradingSeason, MultipleOrder
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHightide import IHightide
from contracts.libraries.CommonLibrary import (
    CommonLib,
    get_contract_version,
    get_registry_address,
    set_contract_version,
    set_registry_address,
)

// CAVEAT - This contract is not tested yet
// This contract can be used as a source of truth for all consumers of trade stats off-chain/on-chain
// This does not have functions to calculate any of the hightide formulas
// This contract just does on-chain trade stats storage and reporting
// The consumers of these stats should perform necessary calculations
// pair_id as used in this contract refers to market_id - it can be supplied by caller or retrieved from Market contract
// if the asset / collateral id is supplied

@event
func trade_recorded(
    season_id: felt,
    pair_id: felt,
    trader_address: felt,
    order_type: felt,
    order_size: felt,
    order_price: felt,
) {
}
// this var stores the total number of recorded trades for a volume_type
// this is identified by VolumeMetaData (season, pair, order_type)
@storage_var
func num_orders(volume_type: VolumeMetaData) -> (res: felt) {
}

// corresponding to a volume_type and index this storage var stores an actual volume data (size, price, timestamp of record)
@storage_var
func orders(volume_type: VolumeMetaData, index: felt) -> (res: OrderVolume) {
}

// this stores the number of trades in a day for a pair in a season
@storage_var
func trade_frequency(season_id: felt, pair_id: felt, day: felt) -> (res: felt) {
}

// this stores number of traders for a pair in a season
@storage_var
func num_traders(season_id: felt, pair_id: felt) -> (res: felt) {
}

// stores list of trader addresses for a pair in a season - retrievable by index in the list
@storage_var
func traders_in_pair(season_id: felt, pair_id: felt, index: felt) -> (trader_address: felt) {
}

// stores whether a trader is an active trader for a pair in a season i.e. has traded at least once
@storage_var
func trader_for_pair(season_id: felt, pair_id: felt, trader_address: felt) -> (is_trader: felt) {
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

// @dev - This function returns a required number of orders starting from an index for <season_id, pair_id>
// It supports pagination through the use of num_order_required_ and index_from_ params
// This might be used to calculate x_1 according to the hightide algorithm
@view
func get_order_volume{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    volume_type_: VolumeMetaData, num_orders_required_: felt, index_from_: felt
) -> (volume_len: felt, volume: OrderVolume*) {
    alloc_locals;
    with_attr error_message("num_orders_required has to be atleast 1") {
        assert_le(1, num_orders_required_);
    }

    let (volume: OrderVolume*) = alloc();
    let (current_num_orders) = num_orders.read(volume_type_);

    // if there are no trades recorded then return empty list
    if (current_num_orders == 0) {
        return (0, volume);
    }

    with_attr error_message("index is out of range") {
        assert_in_range(index_from_, 0, current_num_orders);
    }
    // we can return minimum of number of orders required and number of orders possible
    let exact_num_orders_required = min_of(current_num_orders - index_from_, num_orders_required_);

    // this function call recursively builds the order volume list to be returned
    collate_volume_data(exact_num_orders_required, index_from_, volume_type_, volume);
    return (exact_num_orders_required, volume);
}

// @dev - Returns current active trader count for given <season_id, pair_id>
// This might be used to calculate x_4 according to the hightide algorithm
@view
func get_num_active_traders{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt
) -> (res: felt) {
    let (current_num_traders) = num_traders.read(season_id_, pair_id_);
    return (current_num_traders,);
}

// @dev - Returns frequency(no. of trades in a day) table(list) for <season_id, pair_id>
// this might be used for calculating x_2 according to the hightide algorithm
@view
func get_season_trade_frequency{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt
) -> (frequency_len: felt, frequency: felt*) {
    alloc_locals;
    let (registry_address) = get_registry_address();
    let (version) = get_contract_version();
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        registry_address, Hightide_INDEX, version
    );

    let (season: TradingSeason) = IHightide.get_season(hightide_address, season_id_);

    // Get current day of the season based on the timestamp
    let current_day = get_current_day(season.start_timestamp);

    local number_of_days;
    let within_season = is_le(current_day, season.num_trading_days - 1);

    // If the season is over, return without setting the trading stats
    if (within_season == 1) {
        assert number_of_days = current_day + 1;
    } else {
        assert number_of_days = season.num_trading_days;
    }

    let frequency_list: felt* = alloc();

    get_frequencies(season_id_, pair_id_, number_of_days, 0, frequency_list);
    return (number_of_days, frequency_list);
}

// @dev - this function returns the number of trades recorded for a particular day upto the timestamp of call
// this might be used for calculating x_2 according to the hightide algorithm
@view
func get_num_trades_in_day{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, day_number_: felt
) -> (res: felt) {
    let (registry_address) = get_registry_address();
    let (version) = get_contract_version();
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        registry_address, Hightide_INDEX, version
    );
    let (season: TradingSeason) = IHightide.get_season(hightide_address, season_id_);

    with_attr error_message(
            "Day number should be less than current day number/total tradable days") {
        assert_lt(day_number_, season.num_trading_days);
    }

    let (current_daily_count) = trade_frequency.read(season_id_, pair_id_, day_number_);
    return (current_daily_count,);
}

// @dev - This function calculates the total number of days in the season for which there was at least 1 trade recorded
// This is used for calculating x_3 according to the hightide algorithm
@view
func get_total_days_traded{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt
) -> (res: felt) {
    alloc_locals;

    let (registry_address) = get_registry_address();
    let (version) = get_contract_version();
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        registry_address, Hightide_INDEX, version
    );
    let (season: TradingSeason) = IHightide.get_season(hightide_address, season_id_);
    // Get current day of the season based on the timestamp
    let current_day = get_current_day(season.start_timestamp);

    local number_of_days;
    let within_season = is_le(current_day, season.num_trading_days - 1);

    // If the season is over, return without setting the trading stats
    if (within_season == 1) {
        assert number_of_days = current_day + 1;
    } else {
        assert number_of_days = season.num_trading_days;
    }

    // The 4th argument of the following function call keeeps a running total of days traded
    let count = count_num_days_traded(season_id_, pair_id_, number_of_days, 0);
    return (count,);
}

//#####################
// External Functions #
//#####################

// @dev - Function called by trading contract after trade execution
@external
func record_trade_batch_stats{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    pair_id_: felt,
    order_size_: felt,
    execution_price_: felt,
    request_list_len: felt,
    request_list: MultipleOrder*,
) {
    alloc_locals;

    let (caller) = get_caller_address();
    let (registry) = get_registry_address();
    let (version) = get_contract_version();

    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    );

    // Get HightideAdmin address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get current season id from hightide
    let (season_id_) = IHightide.get_current_season_id(hightide_address);

    let (current_timestamp) = get_block_timestamp();

    // Get trading season data
    let (season: TradingSeason) = IHightide.get_season(hightide_address, season_id_);

    // Get the current day acc to the season
    let current_day = get_current_day(season.start_timestamp);

    let within_season = is_le(current_day, season.num_trading_days - 1);

    // If the season is over, return without setting the trading stats
    if (within_season == 0) {
        return ();
    }

    let (current_daily_count) = trade_frequency.read(season_id_, pair_id_, current_day);

    // Increment number of trades for current_day
    trade_frequency.write(
        season_id_, pair_id_, current_day, current_daily_count + request_list_len
    );

    // Recursively set the trading stats for each order
    record_trade_batch_stats_recurse(
        season_id_=season_id_,
        pair_id_=pair_id_,
        order_size_=order_size_,
        execution_price_=execution_price_,
        timestamp_=current_timestamp,
        request_list_len_=request_list_len,
        request_list_=request_list,
    );

    return ();
}

//#####################
// Internal Functions #
//#####################

// @dev - Internal function to be called recursively
func record_trade_batch_stats_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    season_id_: felt,
    pair_id_: felt,
    order_size_: felt,
    execution_price_: felt,
    timestamp_: felt,
    request_list_len_: felt,
    request_list_: MultipleOrder*,
) {
    alloc_locals;

    if (request_list_len_ == 0) {
        return ();
    }

    local curr_order_size;

    // Check if size is less than or equal to postionSize
    let cmp_res = is_le(order_size_, [request_list_].positionSize);

    if (cmp_res == 1) {
        // If yes, make the order_size to be size
        assert curr_order_size = order_size_;
    } else {
        // If no, make order_size to be the positionSize̦
        assert curr_order_size = [request_list_].positionSize;
    }

    // Record volume data <size, price>
    let volume_metadata: VolumeMetaData = VolumeMetaData(
        season_id=season_id_, pair_id=pair_id_, order_type=[request_list_].closeOrder
    );

    let (current_len) = num_orders.read(volume_metadata);

    num_orders.write(volume_metadata, current_len + 1);

    // Create order volume type struct object to store
    let order_volume: OrderVolume = OrderVolume(
        size=curr_order_size, price=execution_price_, timestamp=timestamp_
    );

    orders.write(volume_metadata, current_len, order_volume);

    // increment number of trades storage_var
    num_orders.write(volume_metadata, current_len + 1);

    // Update number of unique active traders for a pair in a season
    let (trader_status) = trader_for_pair.read(season_id_, pair_id_, [request_list_].pub_key);

    // If trader was not active for pair in this season
    if (trader_status == 0) {
        // Mark trader as active
        trader_for_pair.write(season_id_, pair_id_, [request_list_].pub_key, 1);
        let (current_num_traders) = num_traders.read(season_id_, pair_id_);
        // Increment count of unique active traders for pair in season
        num_traders.write(season_id_, pair_id_, current_num_traders + 1);
        // Store trader address for pair in this season at current index
        traders_in_pair.write(season_id_, pair_id_, current_num_traders, [request_list_].pub_key);
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // emit event for off-chain consumers
    trade_recorded.emit(
        season_id_,
        pair_id_,
        [request_list_].pub_key,
        [request_list_].closeOrder,
        order_size_,
        execution_price_,
    );

    return record_trade_batch_stats_recurse(
        season_id_,
        pair_id_,
        order_size_,
        execution_price_,
        timestamp_,
        request_list_len_ - 1,
        request_list_ + MultipleOrder.SIZE,
    );
}

// @dev - this function recursively creates the list of order volume
// @param total_required - total number of OrderVolume elements required
// @param index - index of trades storage_var from which to get OrderVolume
// @param volume_type - type of order volume required (season_id, pair_id, order_type)
// @param volume - Pointer of type OrderVolume which stores reference to list location where new order volume will be stored
func collate_volume_data{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    total_required: felt, index: felt, volume_type: VolumeMetaData, volume: OrderVolume*
) {
    if (total_required == 0) {
        return ();
    }
    let current_volume: OrderVolume = orders.read(volume_type, index);
    assert [volume] = current_volume;

    collate_volume_data(total_required - 1, index + 1, volume_type, volume + OrderVolume.SIZE);
    return ();
}

// @dev - returns the minimum of the 2 function arguments
func min_of{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    x: felt, y: felt
) -> felt {
    if (is_le(x, y) == 1) {
        return x;
    }
    return y;
}

// @dev - returns the maximum of the 2 function arguments
func max_of{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    x: felt, y: felt
) -> felt {
    if (is_le(x, y) == 1) {
        return y;
    }
    return x;
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

// @dev - This function recursively calculates the trade count for each day in the season so far
func get_frequencies{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    pair_id_: felt,
    total_frequencies: felt,
    current_index_: felt,
    frequency_list: felt*,
) {
    if (total_frequencies == 0) {
        return ();
    }

    let (current_trade_count) = trade_frequency.read(season_id_, pair_id_, current_index_);
    assert frequency_list[current_index_] = current_trade_count;

    return get_frequencies(
        season_id_, pair_id_, total_frequencies - 1, current_index_ + 1, frequency_list
    );
}

// @dev - This function recursively calculates the total traded days for a season so far
// It checks and counts those days for which trade frequency(count) recorded was atleast 1
// @param days_traded - keeps a running total of the number of days in which there was trade recorded in the season
func count_num_days_traded{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, num_days_: felt, days_traded: felt
) -> felt {
    if (num_days_ == 0) {
        return days_traded;
    }

    let (current_trade_count) = trade_frequency.read(season_id_, pair_id_, num_days_ - 1);
    // If there was no trade recorded, then do not increment days_traded
    if (current_trade_count == 0) {
        return count_num_days_traded(season_id_, pair_id_, num_days_ - 1, days_traded);
    }
    // else increment days_traded to update running total and make the recursive call
    return count_num_days_traded(season_id_, pair_id_, num_days_ - 1, days_traded + 1);
}