%lang starknet

@contract_interface
namespace IInsuranceFund:

    # external functions
    func fund(asset_id_ : felt, amount : felt):
    end

    func defund(asset_id_ : felt, amount : felt):
    end

    func deposit(asset_id_ : felt, amount : felt, position_id_ : felt):
    end

    func withdraw(asset_id_ : felt, amount : felt, position_id_ : felt):
    end

    # view functions
    func balance(asset_id_ : felt) -> (amount : felt):
    end

    func liq_amount(asset_id_ : felt, position_id_ : felt) -> (amount : felt):
    end

end