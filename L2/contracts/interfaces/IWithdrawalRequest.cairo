%lang starknet

from contracts.DataTypes import WithdrawalRequest

@contract_interface
namespace IWithdrawalRequest {
    // External functions

    func add_withdrawal_request(
        request_id_: felt, user_l1_address_: felt, asset_id_: felt, amount_: felt
    ) {
    }

    // View functions

    func get_withdrawal_request_data() -> (
        withdrawal_request_list_len: felt, withdrawal_request_list: WithdrawalRequest*
    ) {
    }
}
