%lang starknet

from contracts.DataTypes import MultipleOrder

@contract_interface
namespace ITrading {
    // external functions
    func execute_batch(
        batch_id: felt,
        quantity_locked: felt,
        market_id: felt,
        oracle_price: felt,
        request_list_len: felt,
        request_list: MultipleOrder*,
    ) -> () {
    }
}
