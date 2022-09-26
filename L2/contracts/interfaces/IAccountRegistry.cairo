%lang starknet

@contract_interface
namespace IAccountRegistry {
    // external functions
    func add_to_account_registry(address_: felt) -> () {
    }

    func remove_from_account_registry(id_: felt) -> () {
    }

    // view functions
    func get_account_registry(starting_index_: felt, num_accounts_: felt) -> (
        account_registry_len: felt, account_registry: felt*
    ) {
    }

    func is_registered_user(address_: felt) -> (present: felt) {
    }
}
