%lang starknet

from contracts.DataTypes import MarketPrice

@contract_interface
namespace IMarketPrices {
    // View functions

    func get_market_price(id: felt) -> (res: MarketPrice) {
    }

    // External functions

    func update_market_price(id: felt, price: felt) {
    }
}
