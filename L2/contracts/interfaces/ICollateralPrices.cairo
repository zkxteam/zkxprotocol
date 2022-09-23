%lang starknet

from contracts.DataTypes import CollateralPrice

@contract_interface
namespace ICollateralPrices {
    // external functions
    func update_collateral_price(id: felt, price: felt) {
    }

    // view functions
    func get_collateral_price(id: felt) -> (res: CollateralPrice) {
    }
}
