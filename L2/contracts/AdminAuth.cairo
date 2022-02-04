%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_equal
from starkware.starknet.common.syscalls import get_caller_address

# @notice Constructor for the contract
# @param address1 - Address for first initial admin
# @param address2 - Address for second initial admin
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        address1 : felt, address2 : felt):
    # Action 0 is the admin role - the role which can add and remove admins
    admin_mapping.write(address=address1, action=0, value=1)
    admin_mapping.write(address=address2, action=0, value=1)
    return ()
end

@storage_var
func admin_mapping(address : felt, action : felt) -> (allowed : felt):
end

# @notice Function to update the permissions
# @param address - Address for which permissions are to be granted/revoked
# @param action - Role that needs to be granted/revoked
# @param value - 0 for revoking, 1 for granting
@external
func update_admin_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        address : felt, action : felt, value : felt):
    # Verify that caller has admin role
    let (caller) = get_caller_address()
    let (is_admin) = admin_mapping.read(address=caller, action=0)
    assert is_admin = 1
    # Add or remove admin action
    if action == 0:
        let (caller) = get_caller_address()
        let status : felt = admin_mapping.read(address=address, action=0)
        # First approval for granting/revoking admin role
        if status == 0:
            admin_mapping.write(address=address, action=0, value=caller)
        # Second approval for granting/revoking admin role
        else:
            assert_not_equal(status, caller)
            admin_mapping.write(address=address, action=0, value=value)
        end
    # All other actions
    else:
        admin_mapping.write(address=address, action=action, value=value)
    end
    return ()
end

# @notice Function to find whether an address has permission to perform a specific role
# @param address - Address for which permission has to be determined
# @param action - Action for which permission has to be determined
# @return allowed - 0 if no access, 1 if access allowed
@view
func get_admin_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        address : felt, action : felt) -> (allowed : felt):
    let (allowed) = admin_mapping.read(address=address, action=action)
    return (allowed=allowed)
end