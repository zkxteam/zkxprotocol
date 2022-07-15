%lang starknet

from contracts.libraries.Utils import verify_caller_authority
from starkware.cairo.common.math import assert_not_zero, assert_nn, assert_le
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.starknet.common.syscalls import call_contract
from contracts.Constants import (
    MasterAdmin_ACTION,
    PubkeyWhitelister_INDEX,
    SigRequirementsManager_INDEX
)
from contracts.DataTypes import CoreFunctionCall, CoreFunction, Signature
from contracts.interfaces.ISigRequirementsManager import ISigRequirementsManager
from contracts.interfaces.IPubkeyWhitelister import IPubkeyWhitelister
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.Utils import SignatureVerification

@storage_var
func registry_address() -> (address:felt):
end

@storage_var
func version() -> (res:felt):
end

@storage_var
func nonce() -> (res: felt):
end

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):

    assert_not_zero(registry_address_)
    assert_not_zero(version_)

    registry_address.write(registry_address_)
    version.write(version_)
    return()
end

func get_num_valid_sig{syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*}(
    num_left_to_validate: felt, num_validated: felt, hash:felt, sig: Signature*, 
    pubkey: felt*, pubkey_whitelister_adddress: felt) -> (res: felt):

    if num_left_to_validate == 0:
        return(num_validated)
    end

    let (is_whitelisted) = IPubkeyWhitelister.is_whitelisted(pubkey_whitelister_adddress, [pubkey])

    if is_whitelisted == 1:

        SignatureVerification.verify_sig(hash, [pubkey], [sig])
        return get_num_valid_sig(num_left_to_validate - 1, 
                                num_validated + 1, 
                                hash, 
                                sig + Signature.SIZE,
                                pubkey + 1,
                                pubkey_whitelister_adddress)
    else:

        return get_num_valid_sig(num_left_to_validate - 1, 
                                num_validated, 
                                hash, 
                                sig + Signature.SIZE,
                                pubkey + 1,
                                pubkey_whitelister_adddress)
    end
end    

@external
func call_core_function{syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*}(
    index: felt, version_: felt, nonce_: felt, function_selector: felt, calldata_len: felt, 
    calldata: felt*, sig_len: felt, sig: Signature*, pubkey_len: felt, pubkey: felt*) -> (
    retdata_len: felt, retdata: felt*):

    alloc_locals
    local core_function_call:CoreFunctionCall = CoreFunctionCall(index,
                                                version_,
                                                nonce_,
                                                function_selector,
                                                calldata_len,
                                                calldata)

    local core_function:CoreFunction = CoreFunction(core_function_call.index,
                                       core_function_call.version,
                                       core_function_call.function_selector)

    # check nonce
    let (current_nonce) = nonce.read()

    assert current_nonce = core_function_call.nonce
    nonce.write(current_nonce+1)

    # check we have equal number of signatures and public keys
    assert sig_len = pubkey_len

    # check whether function being called is handled by the signature infra
    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    let (sig_req_manager_address) = IAuthorizedRegistry.get_contract_address(
                                    current_registry_address,
                                    SigRequirementsManager_INDEX,
                                    current_version)

    ISigRequirementsManager.assert_func_handled(sig_req_manager_address, core_function)

    # get number of required signatures for this call
    let (num_req) = ISigRequirementsManager.get_sig_requirement(sig_req_manager_address, core_function)

    
    assert_le(num_req, sig_len)

    let (hash) = SignatureVerification.calc_call_hash(core_function_call)
    local num_left
    assert num_left = sig_len # we can validate at most sig_len number of signatures

    let (pubkey_whitelister_adddress) = IAuthorizedRegistry.get_contract_address(
                                    current_registry_address,
                                    PubkeyWhitelister_INDEX,
                                    current_version)
    # get number of valid signatures provided
    let (num_sig_provided) = get_num_valid_sig(num_left, 0 , hash, sig, pubkey, pubkey_whitelister_adddress)

    # check that number of signatures provided  >= number of signatures required
    assert_le(num_req, num_sig_provided)

    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    let (contract_address ) = IAuthorizedRegistry.get_contract_address(current_registry_address,
                                                                       core_function_call.index,
                                                                       core_function_call.version)
    let (retdata_len: felt, retdata: felt*) = call_contract(contract_address, 
                                                            core_function_call.function_selector,
                                                            core_function_call.calldata_len,
                                                            core_function_call.calldata)

    return (retdata_len, retdata)
end





@view
func get_registry_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (address:felt):

    let(current_registry_address)=registry_address.read()
    return (current_registry_address)
end

@view
func get_current_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (current_version:felt):

    let (current_version) = version.read()
    return (current_version)
end
