%lang starknet

from contracts.libraries.Utils import verify_caller_authority
from starkware.cairo.common.math import assert_not_zero, assert_nn
from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.Constants import MasterAdmin_ACTION
from contracts.DataTypes import CoreFunction

@storage_var
func registry_address() -> (address:felt):
end

@storage_var
func version() -> (res:felt):
end

@storage_var
func func_to_registration_mapping(core_function: CoreFunction) -> (res:felt):
end

@storage_var
func func_to_num_sig_mapping(core_function: CoreFunction) -> (num: felt):
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


@external
func set_sig_requirement{syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, range_check_ptr}(core_function: CoreFunction, num_req: felt):

    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)

    assert_nn(num_req)

    func_to_registration_mapping.write(core_function, 1)
    func_to_num_sig_mapping.write(core_function, num_req)

    return()
end

@external
func deregister_func{syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, range_check_ptr}(core_function: CoreFunction):

    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)
    func_to_registration_mapping.write(core_function, 0)
    return()
end


@external
func set_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    new_version:felt):

    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)
    version.write(new_version)
    return()
end


@view
func assert_func_handled{syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, range_check_ptr}(core_function: CoreFunction):

    let (is_registered) = func_to_registration_mapping.read(core_function)

    assert_not_zero(is_registered)

    return()
end

@view
func get_sig_requirement{syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, range_check_ptr}(core_function: CoreFunction) -> (num_req: felt):

    let (num_req) = func_to_num_sig_mapping.read(core_function)

    return(num_req)
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

