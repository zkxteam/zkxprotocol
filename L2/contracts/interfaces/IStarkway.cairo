%lang starknet

@contract_interface
namespace IStarkway {
    func get_whitelisted_token_addresses(token_id: felt) -> (addresses_list_len: felt, addresses_list: felt*) {
    }

    func get_native_token_l2_address(token_id: felt) -> (l2_address: felt) {
    }
}