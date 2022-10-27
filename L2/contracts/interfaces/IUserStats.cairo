%lang starknet

from contracts.DataTypes import TraderFee

@contract_interface
namespace IUserStats {
    // external functions
    func record_fee_details(pair_id: felt, trader_fee_list_len: felt, trader_fee_list: TraderFee*) {
    }
}
