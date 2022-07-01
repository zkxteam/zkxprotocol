%lang starknet

@contract_interface
namespace IWithdrawalFeeBalance:
    
    # external functions
    func update_withdrawal_fee_mapping(user_l2_address_ : felt, collateral_id_ : felt, fee_to_add_ : felt):
    end

    # view functions

    func get_total_withdrawal_fee(collateral_id_ : felt) -> (fee : felt):
    end

    func get_user_withdrawal_fee(user_l2_address_ : felt, collateral_id_ : felt) -> (fee : felt):
    end

end