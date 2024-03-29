%lang starknet

from contracts.DataTypes import Constants, HighTideMetaData, Multipliers, RewardToken, TradingSeason

@contract_interface
namespace IHighTide {
    // View functions

    func get_current_season_id() -> (season_id: felt) {
    }

    func get_season(season_id: felt) -> (trading_season: TradingSeason) {
    }

    func get_hightide(hightide_id: felt) -> (hightide_metadata: HighTideMetaData) {
    }

    func get_hightide_reward_tokens(hightide_id: felt) -> (
        reward_tokens_list_len: felt, reward_tokens_list: RewardToken*
    ) {
    }

    func get_season_expiry_state(season_id: felt) -> (is_expired: felt) {
    }

    func get_hightides_by_season_id(season_id: felt) -> (
        hightide_list_len: felt, hightide_list: felt*
    ) {
    }

    func get_multipliers() -> (multipliers: Multipliers) {
    }

    func get_constants() -> (constants: Constants) {
    }

    func is_market_under_hightide(season_id_: felt, market_id_: felt) -> (is_listed: felt) {
    }

    func verify_season_id_exists(season_id_: felt) -> () {
    }
}
