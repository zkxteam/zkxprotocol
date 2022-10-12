%lang starknet

from contracts.DataTypes import MultipleOrder

@contract_interface
namespace ITradingStats {
    // external functions
    func record_trade_batch_stats(
        pair_id_: felt,
        order_size_: felt,
        execution_price_: felt,
        request_list_len: felt,
        request_list: MultipleOrder*,
    ) -> () {
    }
}
