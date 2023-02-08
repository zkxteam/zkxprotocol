%lang starknet

@contract_interface
namespace IFeeDiscount {
    // View functions

    func get_user_tokens(address: felt) -> (value: felt) {
    }

    // External functions

    func increment_governance_tokens(address: felt, value: felt) {
    }

    func decrement_governance_tokens(address: felt, value: felt) {
    }
}
