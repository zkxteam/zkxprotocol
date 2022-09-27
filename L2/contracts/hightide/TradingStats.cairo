%lang starknet

from starkware.starknet.common.syscalls import get_block_timestamp
from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.DataTypes import VolumeMetaData, OrderVolume

// we get the total number of recorded trades for a volume_type 
// this is identified by VolumeMetaData (season, pair, order_type)
@storage_var
func trade_len(volume_type: VolumeMetaData) -> (res: felt) {
}

// corresponding to a volume_type and index this storage var stores an actual volume data (size, price, timestamp of record)

@storage_var
func trades(volume_type: VolumeMetaData, index: felt) -> (res: OrderVolume) {
}

// view function to get trade volume corresponding to a volume_metadata
// it will have option for pagination where it could return only x trades from given index, 
// if this is negative then it returns all

@external
func record_trade_volume{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(pair_id_: felt, order_type_: felt, execution_price_: felt, order_size_: felt) {

    alloc_locals;
    let season_id_ = 0; //HighTideAdmin.get_current_season();
    let volume_metadata:VolumeMetaData = VolumeMetaData(
                                         season_id = season_id_,
                                         pair_id = pair_id_,
                                         order_type = order_type_);
    let (current_len) = trade_len.read(volume_metadata);
    let (current_timestamp) = get_block_timestamp();
    let order_volume: OrderVolume = OrderVolume(
                                    size = order_size_,
                                    price = execution_price_,
                                    timestamp = current_timestamp);
    trades.write(volume_metadata, current_len+1, order_volume);
    return ();
}


