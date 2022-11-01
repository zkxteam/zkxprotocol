%lang starknet

from contracts.DataTypes import MultipleOrder

@contract_interface
namespace ITradingStats {
    // external functions
    func record_trade_batch_stats(
        season_id_: felt,
        pair_id_: felt,
        order_size_64x61_: felt,
        execution_price_64x61_: felt,
        request_list_len: felt,
        request_list: MultipleOrder*,
    ) -> () {
    }
}
