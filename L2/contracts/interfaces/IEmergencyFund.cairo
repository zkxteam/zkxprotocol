%lang starknet

@contract_interface
namespace IEmergencyFund {
    // external functions
    func fund(asset_id_: felt, amount: felt) {
    }

    func defund(asset_id_: felt, amount: felt) {
    }

    func fund_holding(asset_id_: felt, amount: felt) {
    }

    func fund_liquidity(asset_id_: felt, amount: felt) {
    }

    func fund_insurance(asset_id_: felt, amount: felt) {
    }

    func defund_holding(asset_id: felt, amount: felt) {
    }

    func defund_insurance(asset_id: felt, amount: felt) {
    }

    func defund_liquidity(asset_id: felt, amount: felt) {
    }

    // view functions
    func balance(asset_id_: felt) -> (amount: felt) {
    }
}
