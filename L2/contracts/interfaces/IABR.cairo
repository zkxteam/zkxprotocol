%lang starknet

@contract_interface
namespace IABR:
    func get_abr_value(market_id : felt) -> (abr : felt, price : felt, timestamp : felt):
    end
    
    func calculate_abr(
    market_id : felt,
    perp_index_len : felt,
    perp_index : felt*,
    perp_mark_len : felt,
    perp_mark : felt*,
) -> (res : felt):
    end
end
