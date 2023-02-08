%lang starknet

from contracts.DataTypes import CollateralPrice

@contract_interface
namespace ICollateralPrices {
    // View functions

    func get_collateral_price(id: felt) -> (res: CollateralPrice) {
    }

    // External functions

    func update_collateral_price(id: felt, price: felt) {
    }
}
