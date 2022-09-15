%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero

from contracts.Constants import MasterAdmin_ACTION
from contracts.DataTypes import DepositData
from contracts.libraries.Utils import verify_caller_authority

###########
# Storage #
###########

# hold mapping from L2 address, index to DepositData
@storage_var
func L2_address_to_DepositData(address : felt, index : felt) -> (res : DepositData):
end

@storage_var
func num_deposits(address : felt) -> (res : felt):
end

@storage_var
func registry_address() -> (address : felt):
end

@storage_var
func version() -> (res : felt):
end

###############
# Constructor #
###############

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):
    with_attr error_message("Registry address and version cannot be 0"):
        assert_not_zero(registry_address_)
        assert_not_zero(version_)
    end

    registry_address.write(registry_address_)
    version.write(version_)
    return ()
end

##################
# View Functions #
##################

# @notice - returns DepositData array containing all deposits made by a user L2 address
@view
func get_deposit_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt
) -> (res_len : felt, res : DepositData*):
    alloc_locals
    let ret_data : DepositData* = alloc()
    let (local total_deposits) = num_deposits.read(address)

    fill_deposit_data(ret_data, address, total_deposits, 0)

    return (total_deposits, ret_data)
end

@view
func get_registry_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    address : felt
):
    let (current_registry_address) = registry_address.read()
    return (current_registry_address)
end

@view
func get_current_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    current_version : felt
):
    let (current_version) = version.read()
    return (current_version)
end

######################
# External Functions #
######################

# @notice - function to get store DepositData (the user L2 address is picked out from this struct to create mapping)
@external
func store_deposit_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    data : DepositData
):
    # this function will not attempt to interpret the contents of DepositData - we only check that L2 address != 0
    # this function is not permissioned since submission of incorrect data will cost money to the attacker
    # and they will not be able to cancel the transaction anyways since cancellation message has to be sent by originator
    assert_not_zero(data.user_L2_address)
    let (current_num_deposits) = num_deposits.read(data.user_L2_address)

    L2_address_to_DepositData.write(data.user_L2_address, current_num_deposits, data)
    num_deposits.write(data.user_L2_address, current_num_deposits + 1)
    return ()
end

@external
func set_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    new_version : felt
):
    let (current_registry_address) = registry_address.read()
    let (current_version) = version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)
    version.write(new_version)
    return ()
end

######################
# Internal Functions #
######################

# @notice - function to recursively create DepositData array
func fill_deposit_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    data : DepositData*, address : felt, total_deposits : felt, index : felt
):
    if index == total_deposits:
        return ()
    end

    let next_deposit : DepositData = L2_address_to_DepositData.read(address, index)
    assert [data] = next_deposit
    fill_deposit_data(data + DepositData.SIZE, address, total_deposits, index + 1)
    return ()
end
