%lang starknet

from contracts.DataTypes import QuoteL1Message

@contract_interface
namespace IQuoteL1Fee {
    // external functions
    func check_and_add_message(
        user_l1_address_: felt,
        assetID_: felt,
        amount_: felt,
        timestamp_: felt,
        L1_fee_amount_: felt,
        L1_fee_assetID_: felt,
    ) -> (result: felt) {
    }

    // view functions
    func get_withdrawal_request_data(index_) -> (message: QuoteL1Message) {
    }
}
