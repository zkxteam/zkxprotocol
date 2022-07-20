%lang starknet

from contracts.libraries.Utils import verify_caller_authority
from starkware.cairo.common.math import assert_not_zero, assert_nn, assert_le
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.starknet.common.syscalls import call_contract
from contracts.Constants import (
    MasterAdmin_ACTION, PubkeyWhitelister_INDEX, SigRequirementsManager_INDEX)
from contracts.DataTypes import CoreFunctionCall, CoreFunction, Signature
from contracts.interfaces.ISigRequirementsManager import ISigRequirementsManager
from contracts.interfaces.IPubkeyWhitelister import IPubkeyWhitelister
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.Utils import SignatureVerification

@storage_var
func registry_address() -> (address : felt):
end

@storage_var
func version() -> (res : felt):
end

# nonce helps keep track of unique transactions
@storage_var
func nonce() -> (res : felt):
end

# this var stores a master switch
# 0 - no signature check required
# 1 - signature check will be done
@storage_var
func check_sig() -> (res : felt):
end

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        registry_address_ : felt, version_ : felt):
    assert_not_zero(registry_address_)
    assert_not_zero(version_)

    registry_address.write(registry_address_)
    version.write(version_)
    return ()
end

# @notice - goes through the list of signatures and verifies that the hash was signed by the private key
# corresponding to the public key in the same index position
func get_num_valid_sig{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr,
        ecdsa_ptr : SignatureBuiltin*}(
        num_left_to_validate : felt, num_validated : felt, hash : felt, sig : Signature*,
        pubkey : felt*, pubkey_whitelister_adddress : felt) -> (res : felt):
    if num_left_to_validate == 0:
        return (num_validated)
    end

    let (is_whitelisted) = IPubkeyWhitelister.is_whitelisted(pubkey_whitelister_adddress, [pubkey])

    if is_whitelisted == 1:
        # if signature is invalid then the whole call to validator will get reverted
        SignatureVerification.verify_sig(hash, [pubkey], [sig])
        return get_num_valid_sig(
            num_left_to_validate - 1,
            num_validated + 1,
            hash,
            sig + Signature.SIZE,
            pubkey + 1,
            pubkey_whitelister_adddress)
    else:
        return get_num_valid_sig(
            num_left_to_validate - 1,
            num_validated,
            hash,
            sig + Signature.SIZE,
            pubkey + 1,
            pubkey_whitelister_adddress)
    end
end

# @notice - this is the main function which is called by signature nodes
# @param - index, version together give the exact contract address
# @param - function_selector specifies which function to call in the contract
# @param - calldata_len and calldata specify the calldata which needs to be passed on
# @param - sig and pubkey are the signature and public key arrays
@external
func call_core_function{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr,
        ecdsa_ptr : SignatureBuiltin*}(
        index : felt, version_ : felt, nonce_ : felt, function_selector : felt, calldata_len : felt,
        calldata : felt*, sig_len : felt, sig : Signature*, pubkey_len : felt, pubkey : felt*) -> (
        retdata_len : felt, retdata : felt*):
    alloc_locals

    local core_function_call : CoreFunctionCall = CoreFunctionCall(index,
        version_,
        nonce_,
        function_selector,
        calldata_len,
        calldata)

    local core_function : CoreFunction = CoreFunction(core_function_call.index,
        core_function_call.version,
        core_function_call.function_selector)

    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    # check nonce
    let (current_nonce) = nonce.read()

    assert current_nonce = core_function_call.nonce

    # updating nonce here so that there is no re-entrancy
    nonce.write(current_nonce + 1)
    
    # if signature checking has been turned off, then simply forward call to concerned contract
    # without checking

    let (should_check_sig) = check_sig.read()

    if should_check_sig == 0:
        let (contract_address) = IAuthorizedRegistry.get_contract_address(
            current_registry_address, core_function_call.index, core_function_call.version)

        let (retdata_len : felt, retdata : felt*) = call_contract(
            contract_address,
            core_function_call.function_selector,
            core_function_call.calldata_len,
            core_function_call.calldata)
        return (retdata_len, retdata)
    end

    # check we have equal number of signatures and public keys
    assert sig_len = pubkey_len

    # check whether function being called is handled by the signature infra

    let (sig_req_manager_address) = IAuthorizedRegistry.get_contract_address(
        current_registry_address, SigRequirementsManager_INDEX, current_version)

    # if called function is not handled then revert
    ISigRequirementsManager.assert_func_handled(sig_req_manager_address, core_function)

    # get number of required signatures for this call
    let (num_req) = ISigRequirementsManager.get_sig_requirement(
        sig_req_manager_address, core_function)

    # check that atleast the required number of signatures have been given
    assert_le(num_req, sig_len)

    # if 0 signatures are required for the called function, then simply forward the call
    if num_req == 0:
        let (contract_address) = IAuthorizedRegistry.get_contract_address(
            current_registry_address, core_function_call.index, core_function_call.version)

        let (retdata_len : felt, retdata : felt*) = call_contract(
            contract_address,
            core_function_call.function_selector,
            core_function_call.calldata_len,
            core_function_call.calldata)

        return (retdata_len, retdata)
    end

    # calculate the hash of the contract address, nonce, function selector and calldata
    # contract address is represented by index and version
    let (hash) = SignatureVerification.calc_call_hash(core_function_call)
    local num_left
    assert num_left = sig_len  # we can validate at most sig_len number of signatures

    let (pubkey_whitelister_adddress) = IAuthorizedRegistry.get_contract_address(
        current_registry_address, PubkeyWhitelister_INDEX, current_version)
        
    # get number of valid signatures provided
    let (num_sig_provided) = get_num_valid_sig(
        num_left, 0, hash, sig, pubkey, pubkey_whitelister_adddress)

    # check that number of valid signatures provided  >= number of signatures required
    assert_le(num_req, num_sig_provided)

    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    let (contract_address) = IAuthorizedRegistry.get_contract_address(
        current_registry_address, core_function_call.index, core_function_call.version)

    let (retdata_len : felt, retdata : felt*) = call_contract(
        contract_address,
        core_function_call.function_selector,
        core_function_call.calldata_len,
        core_function_call.calldata)

    return (retdata_len, retdata)
end

# @notice - this function switches the signature checking on/off
@external
func toggle_check_sig{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}():
    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)

    let (should_check_sig) = check_sig.read()

    check_sig.write(1 - should_check_sig)
    return ()
end

# @notice - this function returns the current signature check switch status
@view
func get_check_sig{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        res : felt):
    let (should_check_sig) = check_sig.read()
    return (should_check_sig)
end

@view
func get_registry_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        address : felt):
    let (current_registry_address) = registry_address.read()
    return (current_registry_address)
end

@view
func get_current_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        current_version : felt):
    let (current_version) = version.read()
    return (current_version)
end

@view
func get_nonce{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        current_nonce : felt):
    let (current_nonce) = nonce.read()
    return (current_nonce)
end
