%lang starknet

@contract_interface
namespace IABRPayment {
    func pay_abr(
        epoch_: felt, account_addresses_len: felt, account_addresses: felt*, timestamp_: felt
    ) {
    }
}
