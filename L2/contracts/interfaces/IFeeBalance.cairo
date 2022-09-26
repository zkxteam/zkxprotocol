%lang starknet

@contract_interface
namespace IFeeBalance {
    // external functions
    func update_fee_mapping(address: felt, assetID_: felt, fee_to_add: felt) {
    }

    // view functions

    func get_total_fee(assetID_: felt) -> (fee: felt) {
    }

    func get_user_fee(address: felt, assetID_: felt) -> (fee: felt) {
    }
}
