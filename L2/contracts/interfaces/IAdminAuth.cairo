%lang starknet

@contract_interface
namespace IAdminAuth {
    // View functions

    func get_admin_mapping(address: felt, action: felt) -> (allowed: felt) {
    }
}
