%lang starknet

@contract_interface
namespace IABRFund:
    func withdraw(account_address_ : felt, market_id_ : felt, amount_ : felt):
    end

    func deposit(account_address_ : felt, market_id_ : felt, amount_ : felt):
    end
end
