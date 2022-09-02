%lang starknet

@contract_interface
namespace IHolding:
    # external functions
    func fund(asset_id_ : felt, amount : felt):
    end

    func defund(asset_id_ : felt, amount : felt):
    end

    func deposit(asset_id_ : felt, amount : felt):
    end

    func withdraw(asset_id_ : felt, amount : felt):
    end

    # view functions

    func balance(asset_id_ : felt) -> (amount : felt):
    end
end
