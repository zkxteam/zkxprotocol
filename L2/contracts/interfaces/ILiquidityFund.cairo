%lang starknet

@contract_interface
namespace ILiquidityFund {
    // View functions

    func balance(asset_id_: felt) -> (amount: felt) {
    }

    func liq_amount(asset_id_: felt, position_id_: felt) -> (amount: felt) {
    }

    // External functions

    func fund(asset_id_: felt, amount: felt) {
    }

    func defund(asset_id_: felt, amount: felt) {
    }

    func deposit(asset_id_: felt, amount: felt, position_id_: felt) {
    }

    func withdraw(asset_id_: felt, amount: felt, position_id_: felt) {
    }
}
