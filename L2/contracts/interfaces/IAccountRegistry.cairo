%lang starknet

@contract_interface
namespace IAccountRegistry:
    # external functions
    func add_to_account_registry(address_ : felt) -> ():
    end

    func remove_from_account_registry(id_ : felt) -> ():
    end

    # view functions
    func get_account_registry(starting_index_ : felt, num_accounts_ : felt) -> (
        account_registry_len : felt, account_registry : felt*
    ):
    end

    func is_registered_user(address_ : felt) -> (present : felt):
    end
end
