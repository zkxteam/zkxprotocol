%lang starknet

@contract_interface
namespace IABR:
    func get_abr_value(market_id : felt) -> (abr : felt, price : felt, timestamp : felt):
    end
end
