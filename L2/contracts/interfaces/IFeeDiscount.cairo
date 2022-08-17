%lang starknet

@contract_interface
namespace IFeeDiscount:
    # external functions
    func increment_governance_tokens(address : felt, value : felt):
    end

    func decrement_governance_tokens(address : felt, value : felt):
    end

    # view functions
    func get_user_tokens(address : felt) -> (value : felt):
    end
end
