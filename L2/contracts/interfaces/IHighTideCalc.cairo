%lang starknet

@contract_interface
namespace IHighTideCalc {
    // View functions

    func get_funds_flow_per_market(season_id_: felt, market_id_: felt) -> (funds_flow: felt) {
    }

    func get_trader_score_per_market(season_id_: felt, market_id_: felt, trader_address_: felt) -> (
        trader_score: felt
    ) {
    }

    func get_no_of_batches_per_market(season_id_: felt, market_id_: felt) -> (no_of_batches: felt) {
    }

    func get_no_of_users_per_batch() -> (no_of_users: felt) {
    }

    func get_no_of_batches_fetched_per_market(season_id_: felt, market_id_: felt) -> (
        batches_fetched: felt
    ) {
    }

    func get_hightide_state(season_id_: felt, market_id_: felt) -> (state: felt) {
    }

    // External functions

    func calculate_high_tide_factors(season_id_: felt) {
    }

    func calculate_funds_flow(season_id_: felt) {
    }

    func update_no_of_batches_per_market(season_id_: felt) {
    }

    func update_hightide_state_per_market(season_id_: felt, market_id_: felt, state_: felt) {
    }

    func update_no_of_batches_fetched_per_market(
        season_id_: felt, market_id_: felt, batches_fetched_: felt
    ) {
    }
}
