%lang starknet

@contract_interface
namespace IFeeDiscount:

    #external functions
    func add_user_tokens(address : felt, value : felt):
    end

    func remove_user_tokens(address : felt, value : felt):
    end

    #view functions
    func get_user_tokens(address : felt) -> (value : felt):
    end
end