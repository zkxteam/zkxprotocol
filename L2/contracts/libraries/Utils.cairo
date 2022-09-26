%lang starknet
%builtins pedersen range_check ecdsa

from starkware.starknet.common.syscalls import call_contract, get_caller_address, get_tx_info
from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.Constants import AdminAuth_INDEX

from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry

// @notice - helper function to verify authority of caller for action
//  gets admin address from authorized registry
//  asks admin whether caller is authorized for action
func verify_caller_authority{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry: felt, current_version: felt, action: felt
) -> () {
    let (caller) = get_caller_address();
    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=current_version
    );
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=action
    );
    assert access = 1;
    return ();
}
