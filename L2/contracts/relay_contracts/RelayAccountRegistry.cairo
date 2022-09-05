%lang starknet

from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.libraries.RelayLibrary import record_call_details, get_inner_contract, initialize

from starkware.cairo.common.cairo_builtins import HashBuiltin

# @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt, index_ : felt
):
    initialize(registry_address_, version_, index_)
    return ()
end

# @notice - All the following are mirror functions for AccountRegistry.cairo - just record call details and forward call
@external
func add_to_account_registry{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address_ : felt
) -> (res : felt):
    record_call_details('add_to_account_registry')
    let (inner_address) = get_inner_contract()
    let (res) = IAccountRegistry.add_to_account_registry(inner_address, address_)
    return (res)
end

@external
func remove_from_account_registry{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr
}(id_ : felt) -> ():
    record_call_details('remove_from_account_registry')
    let (inner_address) = get_inner_contract()
    IAccountRegistry.remove_from_account_registry(inner_address, id_)
    return ()
end

@view
func get_account_registry{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    starting_index_ : felt, num_accounts_ : felt
) -> (account_registry_len : felt, account_registry : felt*):
    let (inner_address) = get_inner_contract()
    let (res_len, res : felt*) = IAccountRegistry.get_account_registry(
        inner_address, starting_index_, num_accounts_
    )
    return (res_len, res)
end

@view
func is_registered_user{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address_ : felt
) -> (present : felt):
    let (inner_address) = get_inner_contract()
    let (res) = IAccountRegistry.is_registered_user(inner_address, address_)
    return (res)
end
