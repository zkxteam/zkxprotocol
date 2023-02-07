%lang starknet

from contracts.DataTypes import MultipleOrder

@contract_interface
namespace ITrading {
    // View functions

    func get_batch_id_status(batch_id_: felt) -> (status: felt) {
    }

    // External functions

    func execute_batch(
        batch_id_: felt,
        quantity_locked_: felt,
        market_id_: felt,
        oracle_price_: felt,
        request_list_len: felt,
        request_list: MultipleOrder*,
    ) -> () {
    }
}
