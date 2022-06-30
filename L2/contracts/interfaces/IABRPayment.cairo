%lang starknet

@contract_interface
namespace IABRPayment:

    # external functions
    func pay_abr(account_addresses_len : felt, account_addresses : felt*):
    end
    
end