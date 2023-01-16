%lang starknet

@contract_interface
namespace IRewardsCalculation {
    func get_user_xp_value(season_id_: felt, user_address_: felt) -> (xp_value: felt) {
    }

    func get_xp_state(season_id_: felt) -> (state: felt) {
    }

    func update_no_of_batches_in_season(season_id_: felt) {
    }
}
