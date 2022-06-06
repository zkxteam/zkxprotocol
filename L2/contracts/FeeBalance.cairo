%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of AdminAuth contract
@storage_var
func registry_address() -> (contract_address : felt):
end

@storage_var
func fee_mapping(address : felt, assetID : felt) -> (fee : felt):
end

@storage_var
func total_fee_per_asset(assetID : felt) -> (accumulated_fee : felt):
end

# @notice Constructor of the smart-contract
# @param resgitry_address_ Address of the AuthorizedRegistry contract
# @param version_ Version of this contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):
    registry_address.write(value=registry_address_)
    contract_version.write(value=version_)
    return ()
end

# @notice Function to update fee mapping which stores total fee for a user
# @param address - address of the user for whom fee is to be updated
# @param fee_to_add - fee value that is to be added
@external
func update_fee_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt, assetID_ : felt, fee_to_add : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=5, version=version
    )

    with_attr error_message("Access is denied since caller is not trading contract"):
        assert caller = trading_address
    end

    let current_fee : felt = fee_mapping.read(address=address, assetID=assetID_)
    let new_fee : felt = current_fee + fee_to_add
    fee_mapping.write(address=address, assetID=assetID_, value=new_fee)

    let current_total_fee_per_asset : felt = total_fee_per_asset.read(assetID=assetID_)
    let new_total_fee_per_asset : felt = current_total_fee_per_asset + fee_to_add
    total_fee_per_asset.write(assetID=assetID_, value=new_total_fee_per_asset)

    return ()
end

# @notice Function to get the total fee accumulated in the system
# @return fee - total fee in the system
@view
func get_total_fee{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt
) -> (fee : felt):
    let (fee) = total_fee_per_asset.read(assetID=assetID_)
    return (fee)
end

# @notice Function to get the total accumulated fee for a specific user
# @param address - address of the user for whom total fee is to be obtained
# @return fee - total accumulated fee for the user
@view
func get_user_fee{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt, assetID_ : felt
) -> (fee : felt):
    let (fee) = fee_mapping.read(address=address, assetID=assetID_)
    return (fee)
end

# @notice AuthorizedRegistry interface
@contract_interface
namespace IAuthorizedRegistry:
    func get_contract_address(index : felt, version : felt) -> (address : felt):
    end
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end
