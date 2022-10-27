%lang starknet

from contracts.DataTypes import HighTideMetaData, RewardToken, TradingSeason

@contract_interface
namespace IHighTide {
    func get_current_season_id() -> (season_id: felt) {
    }

    func get_season(season_id: felt) -> (trading_season: TradingSeason) {
    }

    func get_hightide(hightide_id: felt) -> (hightide_metadata: HighTideMetaData){
    }

    func get_hightide_reward_tokens(hightide_id: felt) -> (reward_tokens_list_len: felt, reward_tokens_list: RewardToken*) {
    }
}
