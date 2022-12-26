%lang starknet

@contract_interface
namespace IHighTideCalc {
    // ////////
    // View //
    // ////////

    func get_funds_flow_per_market(season_id_: felt, pair_id_: felt) -> (funds_flow: felt) {
    }

    func get_trader_score_per_market(season_id_: felt, pair_id_: felt, trader_address_: felt) -> (
        trader_score: felt
    ) {
    }

    // ////////////
    // External //
    // ////////////

    func calculate_high_tide_factors(season_id_: felt) {
    }

    func calculate_funds_flow(season_id_: felt) {
    }
}
