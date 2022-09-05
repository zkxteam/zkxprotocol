%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.bool import TRUE, FALSE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_equal, assert_lt, assert_nn, assert_le
from starkware.starknet.common.syscalls import get_caller_address
from contracts.Constants import MasterAdmin_ACTION

###########
# Storage #
###########

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

# stores the minimum number of admins required to be in the system
# this number can be > current total admins in the system since this number is only used to check whether
# admin removal is possible
@storage_var
func min_num_admins() -> (res : felt):
end

# stores previous approver for an address (used to update MasterAdmin_ACTION)
@storage_var
func approver(address : felt) -> (approver_address : felt):
end

# stores previous remover (the admin which proposed removal) for an address (used to update MasterAdmin_ACTION)
@storage_var
func remover(address : felt) -> (remover_address : felt):
end

# stores the number of admins currently in the system
@storage_var
func current_total_admins() -> (res : felt):
end

###############
# Constructor #
###############

# @notice Constructor for the contract
# @param address1 - Address for first initial admin
# @param address2 - Address for second initial admin
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address1 : felt, address2 : felt
):
    # Action 0 is the admin role - the role which can add and remove admins
    admin_mapping.write(address=address1, action=MasterAdmin_ACTION, value=TRUE)
    admin_mapping.write(address=address2, action=MasterAdmin_ACTION, value=TRUE)
    min_num_admins.write(2)
    current_total_admins.write(2)
    return ()
end

##################
# View Functions #
##################

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

# @notice - Returns minimum number of admins required in the system
@view
func get_min_num_admins{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (res) = min_num_admins.read()
    return (res)
end

# @notice - Returns the total number of admins currently in the system
@view
func get_current_total_admins{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (res : felt):
    let (res) = current_total_admins.read()
    return (res)
end

######################
# External Functions #
######################

# @notice Function to update the permissions
# @param address - Address for which permissions are to be granted/revoked
# @param action - Role that needs to be granted/revoked
# @param value - 0 (FALSE) for revoking, 1 (TRUE) for granting
@external
func update_admin_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt, action : felt, value : felt
):
    # Verify that caller has admin role
    let (caller) = get_caller_address()
    let (is_admin) = admin_mapping.read(address=caller, action=MasterAdmin_ACTION)

    with_attr error_message("Unauthorized call - only admin can call this function"):
        assert is_admin = TRUE
    end

    # if current permission for <address, action> is same as value then simply return without any processing
    let (current_val) = admin_mapping.read(address=address, action=action)
    if current_val == value:
        return ()
    end

    # arg value should either be 0 or 1
    with_attr error_message("Permission can only be 0 or 1"):
        let val_check = value * (1 - value)
        assert val_check = FALSE
    end

    # Add or remove admin action
    if action == MasterAdmin_ACTION:
        process_admin_action(address, value, caller)
        return ()
        # All other actions
    else:
        admin_mapping.write(address=address, action=action, value=value)
        return ()
    end
end

# @notice - Callable only by admin, this function sets the minimum number of admins that should be present in the system
# @param num - number of min admins to set (must be >= 2)
@external
func set_min_num_admins{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    num : felt
):
    # Verify that caller has admin role
    let (caller) = get_caller_address()
    let (is_admin) = admin_mapping.read(address=caller, action=MasterAdmin_ACTION)

    with_attr error_message("Unauthorized call - only admin can call this function"):
        assert is_admin = TRUE
    end

    with_attr error_message("Incorrect value for minimum number of admins - should be >=2"):
        assert_nn(num)
        assert_le(2, num)  # we enforce that there have to be atleast 2 admins in the system
    end

    min_num_admins.write(num)
    return ()
end

######################
# Internal Functions #
######################

# @notice - This function processes the update admin mapping call when action = MasterAdmin_ACTION
# It checks that caller is not the same as previous approver/remover and updates the mapping accordingly
func process_admin_action{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt, value : felt, caller : felt
):
    if value == TRUE:
        # check that approver is not same as caller
        # if present approver is 0 then caller is first approver
        # save caller address as approver & return
        let (current_approver) = approver.read(address)
        with_attr error_message("Both approvers cannot be the same"):
            assert_not_equal(current_approver, caller)
        end
        if current_approver == 0:
            approver.write(address, caller)
            return ()
        else:
            # if present approver != 0, then this is 2nd approval
            # give admin permission to address and mark approver address as 0 for future approvals
            admin_mapping.write(address, MasterAdmin_ACTION, TRUE)
            approver.write(address, 0)  # this ensures that if address gets removed as admin, it would again need 2 approvals
            let (current_num_admins) = current_total_admins.read()
            current_total_admins.write(current_num_admins + 1)  # increment number of admins in the system
            return ()
        end
    else:
        # verify that we have more than minimum number of admins in the system
        # proceed with removal process only if condition is satisfied
        let (minimum_admins_required) = min_num_admins.read()
        let (current_num_admins) = current_total_admins.read()

        with_attr error_message("Cannot have less than minimum number of admins"):
            assert_lt(minimum_admins_required, current_num_admins)
        end

        # check that remover is not the same as caller
        let (current_remover) = remover.read(address)
        with_attr error_message("Both removers cannot be the same"):
            assert_not_equal(current_remover, caller)
        end
        if current_remover == 0:
            # if present remover is 0 then caller is first remover
            # save caller address as remover & return
            remover.write(address, caller)
            return ()
        else:
            # if present remover !=0, then this is 2nd removal call
            # revoke admin permission for address and mark remover as 0 for future removals
            admin_mapping.write(address, MasterAdmin_ACTION, FALSE)
            # this ensures that if address is added as admin, it would need 2 removals to revoke admin permission
            remover.write(address, 0)
            let (current_num_admins) = current_total_admins.read()
            current_total_admins.write(current_num_admins - 1)  # decrement number of admins in the system
            return ()
        end
    end
end
