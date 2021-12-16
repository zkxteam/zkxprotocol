%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.cairo.common.math import assert_not_equal
from starkware.starknet.common.syscalls import get_caller_address

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

@external
func update_admin_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        address : felt, action : felt):
    # Verify that caller has admin role
    let (caller) = get_caller_address()
    let (is_admin) = admin_mapping.read(address=caller, action=0)
    assert_not_zero(is_admin)
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
            admin_mapping.write(address=address, action=0, value=1)
        end
    # All other actions
    else:
        admin_mapping.write(address=address, action=action, value=1)
    end
    return ()
end

@view
func get_admin_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        address : felt, action : felt) -> (allowed : felt):
    let (allowed) = admin_mapping.read(address=address, action=action)
    return (allowed=allowed)
end