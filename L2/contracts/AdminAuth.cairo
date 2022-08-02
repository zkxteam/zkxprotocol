%lang starknet

%builtins pedersen range_check ecdsa

from contracts.Constants import MasterAdmin_ACTION
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_equal, assert_lt, assert_nn, assert_le
from starkware.cairo.common.bool import TRUE, FALSE
from starkware.starknet.common.syscalls import get_caller_address

#### STORAGE VARS ####
# @notice Stores the access permissions
# Action - role
# 0 - Master admin
# 1 - Manage assets
# 2 - Manage markets
# 3 - Manage auth registry
# 4 - Manage fee details
# 5 - Manage all funds
# ref Constants.cairo
@storage_var
func admin_mapping(address : felt, action : felt) -> (allowed : felt):
end

@storage_var
func min_num_admins() -> (res: felt):
end

@storage_var
func approver(address: felt) -> (approver_address: felt):
end

@storage_var
func remover(address: felt) -> (remover_address: felt):
end

@storage_var
func current_total_admins() -> (res: felt):
end


# @notice Constructor for the contract
# @param address1 - Address for first initial admin
# @param address2 - Address for second initial admin
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address1 : felt, address2 : felt
):
    # Action 0 is the admin role - the role which can add and remove admins
    admin_mapping.write(address=address1, action=MasterAdmin_ACTION, value=1)
    admin_mapping.write(address=address2, action=MasterAdmin_ACTION, value=1)
    min_num_admins.write(2)
    return ()
end

#### VIEW FUNCTIONS ####

# @notice Function to find whether an address has permission to perform a specific role
# @param address - Address for which permission has to be determined
# @param action - Action for which permission has to be determined
# @return allowed - 0 if no access, 1 if access allowed
@view
func get_admin_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt, action : felt
) -> (allowed : felt):
    let (allowed) = admin_mapping.read(address=address, action=action)
    return (allowed=allowed)
end

@view
func get_min_num_admins{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
) -> (res: felt):

    let (res) = min_num_admins.read()
    return(res)
end

#### EXTERNAL FUNCTIONS ####

# @notice Function to update the permissions
# @param address - Address for which permissions are to be granted/revoked
# @param action - Role that needs to be granted/revoked
# @param value - 0 for revoking, 1 for granting
@external
func update_admin_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt, action : felt, value : felt
):
    # Verify that caller has admin role
    let (caller) = get_caller_address()
    let (is_admin) = admin_mapping.read(address=caller, action=MasterAdmin_ACTION)
    assert is_admin = TRUE

    # if current permission for <address, action> is same as value then simply return without any processing
    let (current_val) = admin_mapping.read(address=address, action=action)
    if current_val == value:
        return()
    end

    # arg value should either be 0 or 1
    with_attr error_message("Permission can only be 0 or 1"):
        let val_check = value * (1-value)
        assert val_check = FALSE
    end

    # Add or remove admin action
    if action == MasterAdmin_ACTION:

        process_admin_action(address, value, caller)
        return()
        # All other actions
    else:
        admin_mapping.write(address=address, action=action, value=value)
        return()
    end
    
end

@external
func set_min_num_admins{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    num: felt
):

    # Verify that caller has admin role
    let (caller) = get_caller_address()
    let (is_admin) = admin_mapping.read(address=caller, action=MasterAdmin_ACTION)
    assert is_admin = TRUE

    assert_nn(num)
    assert_le(2, num) # we enforce that there have to be atleast 2 admins in the system
    min_num_admins.write(num)
    return()
end



#### INTERNAL FUNCTIONS ####
func process_admin_action{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address: felt, value: felt, caller: felt
):
    if value == TRUE:
        # check that approver is not same as caller
        # if present approver is 0 then caller is first approver
        # save caller address as approver & return
        let (current_approver) = approver.read(address)
        assert_not_equal(current_approver, caller)
        if current_approver == 0:
            approver.write(address, caller)
            return()
        else:
            # if present approver != 0, then this is 2nd approval
            # give admin permission to address and mark approver address as 0 for future approvals
            admin_mapping.write(address, MasterAdmin_ACTION, TRUE)
            approver.write(address, 0) # this ensures that if address gets removed as admin, it would again need 2 approvals
            let (current_num_admins) = current_total_admins.read()
            current_total_admins.write(current_num_admins+1) # increment number of admins in the system
            return()
        end
    else:

        # verify that we have more than minimum number of admins in the system
        # proceed with removal process only if condition is satisfied
        let (minimum_admins_required) = min_num_admins.read()
        let (current_num_admins) = current_total_admins.read()
        assert_lt(minimum_admins_required, current_num_admins)
    
        # check that remover is not the same as caller
        let (current_remover) = remover.read(address)
        assert_not_equal(current_remover, caller)
        if current_remover == 0:
            # if present remover is 0 then  caller is first remover
            # save caller address as remover & return
            remover.write(address, caller)
            return()
        else:
            # if presentremover !=0, then this is 2nd removal call
            # revoke admin permission for address and mark remover as 0 for future removals
            admin_mapping.write(address, MasterAdmin_ACTION, FALSE)
            # this ensures that if address is added as admin, it would need 2 removals to revoke admin permission
            remover.write(address, 0) 
            let (current_num_admins) = current_total_admins.read()
            current_total_admins.write(current_num_admins-1) # decrement number of admins in the system
            return()
        end
    end
end






