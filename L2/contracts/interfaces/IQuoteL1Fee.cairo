%lang starknet

from contracts.DataTypes import QuoteL1Message

@contract_interface
namespace IQuoteL1Fee {
    ////////////////////////
    // External Functions //
    ////////////////////////

    func check_and_add_message(
        user_l1_address_: felt,
        asset_id_: felt,
        amount_: felt,
        timestamp_: felt,
        L1_fee_amount_: felt,
        L1_fee_asset_id_: felt,
    ) -> (result: felt) {
    }

    ////////////////////
    // View functions //
    ////////////////////

    func get_withdrawal_request_data(index_) -> (message: QuoteL1Message) {
    }
}
