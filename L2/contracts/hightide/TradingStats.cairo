%lang starknet

from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import unsigned_div_rem
from contracts.Constants import Hightide_INDEX
from contracts.DataTypes import VolumeMetaData, OrderVolume, TradingSeason
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHightideAdmin import IHightideAdmin
from contracts.libraries.CommonLibrary import (
CommonLib, 
get_contract_version, 
get_registry_address, 
set_contract_version,
set_registry_address
)

// we get the total number of recorded trades for a volume_type 
// this is identified by VolumeMetaData (season, pair, order_type)
@storage_var
func num_trades(volume_type: VolumeMetaData) -> (res: felt) {
}

// corresponding to a volume_type and index this storage var stores an actual volume data (size, price, timestamp of record)

@storage_var
func trades(volume_type: VolumeMetaData, index: felt) -> (res: OrderVolume) {
}

@storage_var
func trade_frequency(season_id:felt, pair_id: felt, day: felt) -> (res:felt) {
}

@storage_var
func num_traders(season_id: felt, pair_id: felt) -> (res: felt) {
}

// stores list of trader addresses for a pair in a season
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


// view function to get trade volume corresponding to a volume_metadata
// it will have option for pagination where it could return only 'x' trades from given index, 
// if this is negative then it returns all

@external
func record_trade_stats{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(pair_id_: felt, order_type_: felt, execution_price_: felt, order_size_: felt) {

    alloc_locals;

    let (registry_address) = get_registry_address();
    let (version) = get_contract_version();

    let (hightide_address) = IAuthorizedRegistry.get_contract_address(registry_address, Hightide_INDEX, version);
    let (season_id_) = IHightideAdmin.get_current_season_id(hightide_address); 
    // Record volume data <size, price>
    let volume_metadata:VolumeMetaData = VolumeMetaData(
                                         season_id = season_id_,
                                         pair_id = pair_id_,
                                         order_type = order_type_);
    let (current_len) = num_trades.read(volume_metadata);
    let (current_timestamp) = get_block_timestamp();
    let order_volume: OrderVolume = OrderVolume(
                                    size = order_size_,
                                    price = execution_price_,
                                    timestamp = current_timestamp);

    trades.write(volume_metadata, current_len, order_volume);
    // update number of trade storage_var
    num_trades.write(volume_metadata, current_len+1);

    // Get trading season data
    let (season: TradingSeason) = IHightideAdmin.get_season(hightide_address, season_id_);

    local time_since_start = current_timestamp-season.start_timestamp;

    //Calculate current day = S/number of seconds in a day where S=time since start of season
    let (current_day,r) = unsigned_div_rem(time_since_start,24*60*60);
    let (current_daily_count) = trade_frequency.read(season_id_, pair_id_,current_day);
    trade_frequency.write(season_id_,pair_id_,current_day, current_daily_count+1);

    //Update number of unique active traders for a pair in a season
    let (trader_address) = get_caller_address();
    let (trader_status) = trader_for_pair.read(season_id_, pair_id_, trader_address);
    // If trader was not active for pair in this season
    if (trader_status==0) {
        // Mark trader as active
        trader_for_pair.write(season_id_,pair_id_,trader_address,1);
        let (current_num_traders) = num_traders.read(season_id_, pair_id_);
        // Increment count of uniqie active traders for pair in season
        num_traders.write(season_id_, pair_id_, current_num_traders + 1);
        // Store trader address for pair in this season at current index
        traders_in_pair.write(season_id_, pair_id_, current_num_traders, trader_address);
        return ();
    }
    return ();
    
}


