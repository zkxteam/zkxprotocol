%lang starknet

from contracts.DataTypes import Market, MarketWID

@contract_interface
namespace IMarkets {
    ////////////////////////
    // External functions //
    ////////////////////////

    func add_market(id: felt, newMarket: Market) {
    }

    func remove_market(id: felt) {
    }

    func modify_leverage(id: felt, leverage: felt) {
    }

    func modify_tradable(id: felt, tradable: felt) {
    }

    func change_max_ttl(new_max_ttl: felt) {
    }

    func change_max_leverage(new_max_leverage: felt) {
    }

    ////////////////////
    // View functions //
    ////////////////////

    func get_collateral_from_market(market_id_: felt) -> (collateral_id: felt) {
    }

    func get_asset_collateral_from_market(market_id_: felt) -> (
        asset_id: felt, collateral_id: felt
    ) {
    }

    func get_ttl_from_market(market_id_: felt) -> (ttl: felt) {
    }

    func get_market(market_id_: felt) -> (currMarket: Market) {
    }

    func get_maintenance_margin(market_id_: felt) -> (maintenance_margin: felt) {
    }

    func get_market_id_from_assets(asset_id_: felt, collateral_id_: felt) -> (market_id: felt) {
    }

    func get_all_markets() -> (array_list_len: felt, array_list: MarketWID*) {
    }

    func get_all_markets_by_state(is_tradable_: felt, is_archived_: felt) -> (array_list_len: felt, array_list: Market*) {
    }
}
