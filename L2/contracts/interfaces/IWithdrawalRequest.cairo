%lang starknet

from contracts.DataTypes import WithdrawalRequest

@contract_interface
namespace IWithdrawalRequest:
    
    # external functions
    func add_withdrawal_request(user_l1_address_ : felt, collateral_id_ : felt, amount_ : felt, timestamp_ : felt):
    end

    # view functions
    func get_withdrawal_request_data() -> (withdrawal_request_list_len : felt, 
                                        withdrawal_request_list : WithdrawalRequest*):
    end

end