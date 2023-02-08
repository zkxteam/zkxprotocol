%lang starknet

@contract_interface
namespace IAccountRegistry {
    // View functions

    func get_account_registry(starting_index_: felt, num_accounts_: felt) -> (
        account_registry_len: felt, account_registry: felt*
    ) {
    }

    func is_registered_user(address_: felt) -> (present: felt) {
    }

    func get_batch(starting_index_: felt, ending_index_: felt) -> (
        account_registry_len: felt, account_registry: felt*
    ) {
    }

    func get_registry_len() -> (len: felt) {
    }

    // External functions

    func add_to_account_registry(address_: felt) -> () {
    }

    func remove_from_account_registry(id_: felt) -> () {
    }
}
