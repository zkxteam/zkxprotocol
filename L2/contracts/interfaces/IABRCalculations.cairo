%lang starknet

@contract_interface
namespace IABRCalculations {
    func calculate_abr(
        perp_index_len: felt, perp_index: felt*, perp_mark_len: felt, perp_mark: felt*
    ) -> (abr_value: felt, abr_last_price: felt) {
    }
}
