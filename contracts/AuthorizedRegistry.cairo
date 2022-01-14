%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address

# @notice Stores the address of AdminAuth contract
@storage_var
func auth_address() -> (contract_address : felt):
end

# @notice Stores the allowance of certain addresses to perform actions
@storage_var
func contract_registry(address : felt, action : felt) -> (allowed : felt):
end

# @notice Constructor for the smart-contract
# @param _authAddress - Address of the AdminAuth Contract
@constructor
func constructor{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(
    _authAddress: felt
):
    auth_address.write(value = _authAddress)

    return ()
end

# @notice Function to modify trusted contracts registry only callable by the admins with action access=3
# @param contract_address - Address of the contract that needs to be updated
# @param action - Action that should be updated for the address
# @param value - New allowance for the given action for the given address
@external
func update_registry{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(
    contract_address: felt,
    action: felt,
    value: felt
):
    alloc_locals

    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 3)
    assert_not_zero(access)

    # Update the registry
    contract_registry.write(address=contract_address, action=action, value=value)
    return ()
end

# @notice Function to find whether an address has permission to perform certain action
# @param address - Address for which permission has to be determined
# @param action - Action for which permission has to be determined
# @return allowed - 0 if no access, 1 if access allowed
@view
func get_registry_value{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        address : felt, action : felt) -> (allowed : felt):
    let (allowed) = contract_registry.read(address=address, action=action)
    return (allowed=allowed)
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end