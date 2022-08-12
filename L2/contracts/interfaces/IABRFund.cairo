%lang starknet

@contract_interface
namespace IABRFund:
    func withdraw(order_id_ : felt, market_id_ : felt, amount : felt):
    end

    func deposit(order_id_ : felt, market_id_ : felt, amount : felt):
    end
end
