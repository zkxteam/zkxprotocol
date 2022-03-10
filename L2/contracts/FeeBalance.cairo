%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero

@storage_var
func auth_address() -> (contract_address : felt):
end

@storage_var
func caller_address() -> (contract_address : felt):
end

@storage_var
func fee_mapping(address : felt, assetID : felt) -> (fee : felt):
end

@storage_var
func total_fee_per_asset(assetID: felt) -> (accumulated_fee : felt):
end

# @notice Constructor of the smart-contract
# @param _authAddress - Address of the adminAuth contract
@constructor
func constructor{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(_authAddress : felt):

    auth_address.write(value = _authAddress)
    return ()
end

# @notice Funtion to update caller address which can only call update_fee_mapping()
# @param address - address of the caller
@external
func update_caller_address{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(
    address: felt,
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 0)
    assert_not_zero(access)
    caller_address.write(value=address)
    return()
end

# @notice Function to update fee mapping which stores total fee for a user
# @param address - address of the user for whom fee is to be updated
# @param fee_to_add - fee value that is to be added
@external
func update_fee_mapping{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(
    address: felt,
    assetID_: felt,
    fee_to_add: felt
):
    let (caller) = get_caller_address()
    let (caller_addr) = caller_address.read()
    assert caller = caller_addr

    let current_fee : felt = fee_mapping.read(address=address, assetID = assetID_)
    let new_fee: felt = current_fee + fee_to_add
    fee_mapping.write(address=address, assetID = assetID_, value=new_fee)

    let current_total_fee_per_asset : felt = total_fee_per_asset.read(assetID = assetID_)
    let new_total_fee_per_asset: felt = current_total_fee_per_asset + fee_to_add
    total_fee_per_asset.write(assetID = assetID_, value=new_total_fee_per_asset)

    return ()
end

# @notice Function to get the total fee accumulated in the system
# @return fee - total fee in the system
@view
func get_total_fee{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(
    assetID_: felt 
) -> (
    fee: felt
): 
    let (fee) = total_fee_per_asset.read(assetID=assetID_)
    return (fee)
end

# @notice Function to get the total accumulated fee for a specific user
# @param address - address of the user for whom total fee is to be obtained
# @return fee - total accumulated fee for the user
@view
func get_user_fee{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(
    address: felt,
    assetID_: felt,
) -> (
    fee: felt
): 
    let (fee) = fee_mapping.read(address=address, assetID=assetID_)
    return (fee)
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end