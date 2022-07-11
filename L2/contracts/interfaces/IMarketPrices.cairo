%lang starknet

from contracts.DataTypes import MarketPrice

@contract_interface
namespace IMarketPrices:

    # external functions
    func update_market_price(id : felt, price : felt):
    end

    # view functions
    func get_market_price(id : felt) -> (res : MarketPrice):
    end
end