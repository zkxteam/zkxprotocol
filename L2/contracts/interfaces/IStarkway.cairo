%lang starknet

@contract_interface
namespace IStarkway {
    func get_token_contract_addresses(token_id: felt) -> (contract_address_list_len: felt, contract_address_list: felt*) {
    }
}