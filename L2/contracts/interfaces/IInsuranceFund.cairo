%lang starknet

@contract_interface
namespace IInsuranceFund {
    // external functions
    func fund(asset_id_: felt, amount: felt) {
    }

    func defund(asset_id_: felt, amount: felt) {
    }

    func deposit(asset_id_: felt, amount: felt, position_id_: felt) {
    }

    func withdraw(asset_id_: felt, amount: felt, position_id_: felt) {
    }

    // view functions
    func balance(asset_id_: felt) -> (amount: felt) {
    }

    func liq_amount(asset_id_: felt, position_id_: felt) -> (amount: felt) {
    }
}
