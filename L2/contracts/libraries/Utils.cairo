%lang starknet
%builtins pedersen range_check ecdsa

from starkware.starknet.common.syscalls import call_contract, get_caller_address, get_tx_info
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.signature import (
    verify_ecdsa_signature
)
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.Constants import (
    AdminAuth_INDEX
)

from contracts.DataTypes import RouterFunctionCall
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from starkware.cairo.common.hash_state import (
    hash_init,
    hash_finalize,
    hash_update_with_hashchain,
    hash_update_single,
)


# @notice - helper function to verify authority of caller for action
# gets admin address from authorized registry
# asks admin whether caller is authorized for action
func verify_caller_authority{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*,
        range_check_ptr}(registry:felt, current_version:felt, action:felt) -> ():


    let (caller) = get_caller_address()
    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=current_version)
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=action
        )

    assert access = 1
    return()    
end

namespace SignatureVerification:

    func verify_sig{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*,
        range_check_ptr, ecdsa_ptr: SignatureBuiltin*}(hash: felt, public_key: felt, sig: (felt,felt)):

        verify_ecdsa_signature(message=hash,
                               public_key=public_key,
                               signature_r=sig[0],
                               signature_s=sig[1])
        return()
    end

    func calc_call_hash{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*,
        range_check_ptr}(data:RouterFunctionCall) -> (hash:felt):

        let hash_ptr = pedersen_ptr
        with hash_ptr:
          let (hash_state_ptr) = hash_init()
          let (hash_state_ptr) = hash_update_single(hash_state_ptr, data.index)
          let (hash_state_ptr) = hash_update_single(hash_state_ptr, data.version)
          let (hash_state_ptr) = hash_update_single(hash_state_ptr, data.nonce)
          let (hash_state_ptr) = hash_update_single(hash_state_ptr, data.function_selector)
          let (hash_state_ptr) = hash_update_with_hashchain(hash_state_ptr, data.calldata, data.calldata_size)
          let (hash) = hash_finalize(hash_state_ptr)
          return(hash)
        end
    end
end

