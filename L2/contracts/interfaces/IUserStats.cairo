%lang starknet

@contract_interface
namespace IUserStats {
    // external functions
    func record_trader_fee(pair_id: felt, trader_address: felt, fee_64x61: felt) {
    }

    func record_total_fee(pair_id: felt, fee_64x61: felt) {
    }
}
