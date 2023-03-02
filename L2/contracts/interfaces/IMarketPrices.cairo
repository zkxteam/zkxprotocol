%lang starknet

@contract_interface
namespace IMarketPrices {
    // View functions

    func get_market_price(id: felt) -> (market_price: felt) {
    }

    // External functions

    func update_market_price(id: felt, price: felt) {
    }
}
