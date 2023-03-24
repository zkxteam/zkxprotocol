%lang starknet

from contracts.DataTypes import ABRDetails

@contract_interface
namespace IABRCore {
    // View functions

    func get_state() -> (res: felt) {
    }

    func get_epoch() -> (res: felt) {
    }

    func get_bollinger_width() -> (res: felt) {
    }

    func get_base_abr_rate() -> (res: felt) {
    }

    func get_abr_interval() -> (res: felt) {
    }

    func get_markets_remaining() -> (
        remaining_markets_list_len: felt, remaining_markets_list: felt*
    ) {
    }

    func get_no_of_batches_for_current_epoch() -> (res: felt) {
    }

    func get_no_of_users_per_batch() -> (res: felt) {
    }

    func get_remaining_pay_abr_calls() -> (res: felt) {
    }

    func get_next_abr_timestamp() -> (res: felt) {
    }

    func get_abr_details(epoch_: felt, market_id_: felt) -> (
        abr_value: felt, abr_last_price: felt
    ) {
    }

    func get_previous_abr_values(starting_epoch_: felt, market_id_: felt, n_: felt) -> (
        abr_values_list_len: felt, abr_values_list: ABRDetails*
    ) {
    }

    // External functions

    func set_no_of_users_per_batch(new_no_of_users_per_batch: felt) {
    }

    func set_abr_timestamp(new_timestamp: felt) {
    }

    func set_abr_value(
        market_id_: felt,
        perp_index_len: felt,
        perp_index: felt*,
        perp_mark_len: felt,
        perp_mark: felt*,
    ) {
    }

    func make_abr_payments() {
    }

    func set_abr_interval(new_abr_interval_: felt) {
    }

    func set_base_abr_rate(new_base_abr_: felt) {
    }

    func set_bollinger_width(new_bollinger_width_: felt) {
    }
}
