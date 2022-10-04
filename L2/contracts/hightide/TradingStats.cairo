%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import unsigned_div_rem, assert_le, assert_in_range, assert_lt
from starkware.cairo.common.math_cmp import is_nn, is_le
from contracts.Constants import Hightide_INDEX, AccountRegistry_INDEX
from contracts.DataTypes import VolumeMetaData, OrderVolume, TradingSeason
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHighTide import IHighTide
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
    let current_day = get_current_day(hightide_address, season_id_);

    let frequency_list: felt* = alloc();
    local frequency_len = current_day + 1;

    get_frequencies(season_id_, pair_id_, frequency_len, 0, frequency_list);
    return (frequency_len, frequency_list);
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
    // Get current day of the season based on the timestamp
    let current_day = get_current_day(hightide_address, season_id_);

    with_attr error_message(
            "Day number should be less than current day number/total tradable days") {
        assert_le(day_number_, current_day);
    }

    let (current_daily_count) = trade_frequency.read(season_id_, pair_id_, current_day);
    return (current_daily_count,);
}

// @dev - This function calculates the total number of days in the season for which there was at least 1 trade recorded
// This is used for calculating x_3 according to the hightide algorithm
@view
func get_total_days_traded{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt
) -> (res: felt) {
    let (registry_address) = get_registry_address();
    let (version) = get_contract_version();
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        registry_address, Hightide_INDEX, version
    );

    // Get current day of the season based on the timestamp
    let current_day = get_current_day(hightide_address, season_id_);
    // The 4th argument of the following function call keeeps a running total of days traded
    let count = count_num_days_traded(season_id_, pair_id_, current_day + 1, 0);
    return (count,);
}

//#####################
// External Functions #
//#####################

// @dev - This function is called by AccountManager when executing a trade to record data related to a trade
@external
func record_trade_stats{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    pair_id_: felt, order_type_: felt, execution_price_: felt, order_size_: felt
) {
    alloc_locals;
    let (trader_address) = get_caller_address();
    let (registry_address) = get_registry_address();
    let (version) = get_contract_version();
    // Assert that call has come from our deployed AccountManager contract i.e. registered user
    // We could also have the call come from Trading contract - but then trader address has to be given as an argument
    assert_caller_registered(registry_address, version, trader_address);

    // Get HightideAdmin address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        registry_address, Hightide_INDEX, version
    );

    // Get current season id from hightide
    let (season_id_) = IHighTide.get_current_season_id(hightide_address);
    // Record volume data <size, price>
    let volume_metadata: VolumeMetaData = VolumeMetaData(
        season_id=season_id_, pair_id=pair_id_, order_type=order_type_
    );
    let (current_len) = num_orders.read(volume_metadata);
    let (current_timestamp) = get_block_timestamp();

    // Create order volume type struct object to store
    let order_volume: OrderVolume = OrderVolume(
        size=order_size_, price=execution_price_, timestamp=current_timestamp
    );

    orders.write(volume_metadata, current_len, order_volume);
    // increment number of trades storage_var
    num_orders.write(volume_metadata, current_len + 1);

    // emit event for off-chain consumers
    trade_recorded.emit(
        season_id_, pair_id_, trader_address, order_type_, order_size_, execution_price_
    );
    // Get trading season data
    let (season: TradingSeason) = IHighTide.get_season(hightide_address, season_id_);

    local time_since_start = current_timestamp - season.start_timestamp;

    // Calculate current day = S/number of seconds in a day where S=time since start of season
    let (current_day, r) = unsigned_div_rem(time_since_start, 24 * 60 * 60);

    // This error message might not be required since season_id is returned by HightideAdmin
    // and we calculate current_day based on this season_id
    with_attr error_message("Current day cannot exceed max tradable days in season") {
        assert_lt(current_day, season.num_trading_days);
    }
    let (current_daily_count) = trade_frequency.read(season_id_, pair_id_, current_day);
    // Increment number of trades for current_day
    trade_frequency.write(season_id_, pair_id_, current_day, current_daily_count + 1);

    // Update number of unique active traders for a pair in a season

    let (trader_status) = trader_for_pair.read(season_id_, pair_id_, trader_address);
    // If trader was not active for pair in this season
    if (trader_status == 0) {
        // Mark trader as active
        trader_for_pair.write(season_id_, pair_id_, trader_address, 1);
        let (current_num_traders) = num_traders.read(season_id_, pair_id_);
        // Increment count of unique active traders for pair in season
        num_traders.write(season_id_, pair_id_, current_num_traders + 1);
        // Store trader address for pair in this season at current index
        traders_in_pair.write(season_id_, pair_id_, current_num_traders, trader_address);
        return ();
    }
    return ();
}

//#####################
// Internal Functions #
//#####################

// @dev - This function checks that trader address is registered in Account Registry

func assert_caller_registered{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address: felt, version: felt, trader_address: felt
) {
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        registry_address, AccountRegistry_INDEX, version
    );

    let (is_registered) = IAccountRegistry.is_registered_user(
        account_registry_address, trader_address
    );
    with_attr error_message("Trader is not a registered user") {
        assert is_registered = 1;
    }

    return ();
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
    hightide_address: felt, season_id_: felt
) -> felt {
    alloc_locals;
    // Get trading season data
    let (season: TradingSeason) = IHighTide.get_season(hightide_address, season_id_);
    let (current_timestamp) = get_block_timestamp();
    local time_since_start = current_timestamp - season.start_timestamp;

    // Calculate current day = S/number of seconds in a day where S=time since start of season
    let (current_day, r) = unsigned_div_rem(time_since_start, 24 * 60 * 60);
    // If current day number is more than max number of trading days, then return max trading days configured
    let max_current_day = max_of(current_day, season.num_trading_days);
    return max_current_day;
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
    assert [frequency_list] = current_trade_count;
    get_frequencies(
        season_id_, pair_id_, total_frequencies - 1, current_index_ + 1, frequency_list + 1
    );
    return ();
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
