%lang starknet

from contracts.DataTypes import Market, MarketWID

@contract_interface
namespace IMarkets:
    # external functions
    func addMarket(id : felt, newMarket : Market):
    end

    func removeMarket(id : felt):
    end

    func modifyLeverage(id : felt, leverage : felt):
    end

    func modifyTradable(id : felt, tradable : felt):
    end

    func change_max_ttl(new_max_ttl : felt):
    end

    func change_max_leverage(new_max_leverage : felt):
    end
    # view functions
    func getMarket(id : felt) -> (currMarket : Market):
    end

    func getMarket_from_assets(asset_id : felt, collateral_id : felt) -> (market_id : felt):
    end

    func returnAllMarkets() -> (array_list_len : felt, array_list : MarketWID*):
    end

    func get_collateral_from_market(market_id : felt) -> (collateral_id : felt):
    end
end
