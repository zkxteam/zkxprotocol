%lang starknet

from contracts.DataTypes import MultipleOrder, TraderStats

@contract_interface
namespace ITradingStats {
    // view functions
    func get_num_active_traders(season_id_: felt, pair_id_: felt) -> (res: felt) {
    }

    func get_season_trade_frequency(season_id_: felt, pair_id_: felt) -> (
        frequency_len: felt, frequency: felt*
    ) {
    }

    func get_average_order_volume(season_id_: felt, pair_id_: felt) -> (
        average_volume_64x61: felt
    ) {
    }

    func get_max_trades_in_day(season_id_: felt, pair_id_: felt) -> (res: felt) {
    }

    func get_total_days_traded(season_id_: felt, pair_id_: felt) -> (res: felt) {
    }

    // external functions
    func record_trade_batch_stats(
        pair_id_: felt,
        order_size_64x61_: felt,
        execution_price_64x61_: felt,
        request_list_len: felt,
        request_list: MultipleOrder*,
        trader_stats_list_len: felt,
        trader_stats_list: TraderStats*,
    ) -> () {
    }
}
