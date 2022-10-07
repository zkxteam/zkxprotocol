%lang starknet

from contracts.DataTypes import Market

@contract_interface
namespace IMarkets {
    ////////////////////////
    // External functions //
    ////////////////////////

    func add_market(newMarket: Market) {
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

    func get_collateral_from_market(market_id: felt) -> (collateral_id: felt) {
    }

    func get_asset_collateral_from_market(market_id: felt) -> (
        asset_id: felt, collateral_id: felt
    ) {
    }

    func get_ttl_from_market(market_id: felt) -> (ttl: felt) {
    }

    func get_market(id: felt) -> (currMarket: Market) {
    }

    func get_market_from_assets(asset_id: felt, collateral_id: felt) -> (market_id: felt) {
    }

    func get_all_markets() -> (array_list_len: felt, array_list: Market*) {
    }
}