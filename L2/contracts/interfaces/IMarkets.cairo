%lang starknet

from contracts.DataTypes import Market, MarketWID

@contract_interface
namespace IMarkets:
    # external functions
    func add_market(id : felt, newMarket : Market):
    end

    func remove_market(id : felt):
    end

    func modify_leverage(id : felt, leverage : felt):
    end

    func modify_tradable(id : felt, tradable : felt):
    end

    func change_max_ttl(new_max_ttl : felt):
    end

    func change_max_leverage(new_max_leverage : felt):
    end
    # view functions
    func get_market(id : felt) -> (currMarket : Market):
    end

    func get_market_from_assets(asset_id : felt, collateral_id : felt) -> (market_id : felt):
    end

    func get_all_markets() -> (array_list_len : felt, array_list : MarketWID*):
    end
end
