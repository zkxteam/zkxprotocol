%lang starknet

from contracts.DataTypes import MarketPrice

@contract_interface
namespace IMarketPrices {
    // external functions
    func update_market_price(id: felt, price: felt) {
    }

    func set_standard_collateral(collateral_id_: felt) {
    }

    // view functions
    func get_market_price(id: felt) -> (res: MarketPrice) {
    }

    func get_standard_collateral() -> (collateral_id: felt) {
    }
}
