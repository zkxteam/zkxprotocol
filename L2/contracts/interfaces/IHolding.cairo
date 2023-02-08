%lang starknet

@contract_interface
namespace IHolding {
    // View functions

    func balance(asset_id_: felt) -> (amount: felt) {
    }

    // External functions

    func fund(asset_id_: felt, amount: felt) {
    }

    func defund(asset_id_: felt, amount: felt) {
    }

    func deposit(asset_id_: felt, amount: felt) {
    }

    func withdraw(asset_id_: felt, amount: felt) {
    }
}
