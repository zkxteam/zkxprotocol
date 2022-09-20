%lang starknet

@contract_interface
namespace IFeeDiscount {
    // external functions
    func increment_governance_tokens(address: felt, value: felt) {
    }

    func decrement_governance_tokens(address: felt, value: felt) {
    }

    // view functions
    func get_user_tokens(address: felt) -> (value: felt) {
    }
}
