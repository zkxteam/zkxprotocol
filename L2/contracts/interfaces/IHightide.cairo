%lang starknet

from contracts.DataTypes import TradingSeason

@contract_interface
namespace IHightide {
    func get_current_season_id() -> (season_id: felt) {
    }

    func get_season(season_id: felt) -> (trading_season: TradingSeason) {
    }
}
