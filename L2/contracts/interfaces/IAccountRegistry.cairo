%lang starknet

@contract_interface
namespace IAccountRegistry:

    # external functions
    func add_to_account_registry(address_ : felt) -> (res : felt):
    end

    func remove_from_account_registry(id_ : felt) -> (res : felt):
    end

    # view functions
    func get_account_registry() -> (account_registry_len : felt, account_registry : felt*):
    end

end