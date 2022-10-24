%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero, assert_nn
from contracts.Constants import MasterAdmin_ACTION
from contracts.DataTypes import CoreFunction
from contracts.libraries.Utils import verify_caller_authority

//##########
// Events  #
//##########

// this event is emitted whenever a signature requirement is set for any function
@event
func signature_requirement_set(
    index: felt, version: felt, function_selector: felt, num_sig_req: felt
) {
}

// this event is emitted whenever a function is deregistered from the system
@event
func function_deregistered(index: felt, version: felt, function_selector: felt) {
}

//##########
// Storage #
//##########

// this var stores the registry address
@storage_var
func registry_address() -> (address: felt) {
}

// stores contract version
@storage_var
func version() -> (res: felt) {
}

// stores mapping from function -> whether it is registered
@storage_var
func func_to_registration_mapping(core_function: CoreFunction) -> (res: felt) {
}

// stores number of signatures required for a function
@storage_var
func func_to_num_sig_mapping(core_function: CoreFunction) -> (num: felt) {
}

//##############
// Constructor #
//##############

@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    with_attr error_message("SigRequirementsManager: Registry Address or Version cannot be 0") {
        assert_not_zero(registry_address_);
        assert_not_zero(version_);
    }

    registry_address.write(registry_address_);
    version.write(version_);
    return ();
}

//#################
// View Functions #
//#################

// @notice - this function will revert if core function is not registered or has been de-registered
@view
func assert_func_handled{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    core_function: CoreFunction
) {
    let (is_registered) = func_to_registration_mapping.read(core_function);

    with_attr error_message("SigRequirementsManager: Function not registered") {
        assert_not_zero(is_registered);
    }

    return ();
}

// @notice - this function returns number of signatures required for a function
@view
func get_sig_requirement{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    core_function: CoreFunction
) -> (num_req: felt) {
    let (num_req) = func_to_num_sig_mapping.read(core_function);

    return (num_req,);
}

@view
func get_registry_address{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    address: felt
) {
    let (current_registry_address) = registry_address.read();
    return (current_registry_address,);
}

@view
func get_current_version{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    current_version: felt
) {
    let (current_version) = version.read();
    return (current_version,);
}

//#####################
// External Functions #
//#####################

// @notice - function to set number of signature requirement for a function (index, version, selector)
// this also does the function registration (this is the only way to register a function)
// only a function which is registered i.e. func_to_registration_mapping value of 1 is handled by the sig infra
@external
func set_sig_requirement{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    core_function: CoreFunction, num_req: felt
) {
    let (current_registry_address) = registry_address.read();
    let (current_version) = version.read();

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION);

    with_attr error_message("SigRequirementsManager: Number of signatures cannot be negative") {
        assert_nn(num_req);
    }

    func_to_registration_mapping.write(core_function, 1);
    func_to_num_sig_mapping.write(core_function, num_req);
    signature_requirement_set.emit(
        index=core_function.index,
        version=core_function.version,
        function_selector=core_function.function_selector,
        num_sig_req=num_req,
    );
    return ();
}

// @notice - function to deregister a function - callable by admin only
@external
func deregister_func{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    core_function: CoreFunction
) {
    let (current_registry_address) = registry_address.read();
    let (current_version) = version.read();

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION);
    func_to_registration_mapping.write(core_function, 0);
    function_deregistered.emit(
        index=core_function.index,
        version=core_function.version,
        function_selector=core_function.function_selector,
    );
    return ();
}

@external
func set_version{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_version: felt
) {
    let (current_registry_address) = registry_address.read();
    let (current_version) = version.read();

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION);
    version.write(new_version);
    return ();
}
