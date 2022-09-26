%lang starknet

from contracts.DataTypes import Market, MarketWID

@contract_interface
namespace IMarkets {
    // external functions
    func addMarket(id: felt, newMarket: Market) {
    }

    func removeMarket(id: felt) {
    }

    func modifyLeverage(id: felt, leverage: felt) {
    }

    func modifyTradable(id: felt, tradable: felt) {
    }

    func change_max_ttl(new_max_ttl: felt) {
    }

    func change_max_leverage(new_max_leverage: felt) {
    }
    // view functions
    func getMarket(id: felt) -> (currMarket: Market) {
    }

    func getMarket_from_assets(asset_id: felt, collateral_id: felt) -> (market_id: felt) {
    }

    func returnAllMarkets() -> (array_list_len: felt, array_list: MarketWID*) {
    }

    func get_collateral_from_market(market_id: felt) -> (collateral_id: felt) {
    }

    func get_asset_collateral_from_market(market_id: felt) -> (
        asset_id: felt, collateral_id: felt
    ) {
    }

    func get_ttl_from_market(market_id: felt) -> (ttl: felt) {
    }
}
