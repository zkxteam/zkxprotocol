%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of Authorized Registry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# @notice Stores the withdrawal fee charged per asset of each user
@storage_var
func withdrawal_fee_mapping(address : felt, assetID : felt) -> (fee : felt):
end

# @notice Stores the total withdrawal fee per asset
@storage_var
func total_withdrawal_fee_per_asset(assetID : felt) -> (accumulated_fee : felt):
end

# @notice Constructor of the smart-contract
# @param registry_address_ Address of the AuthorizedRegistry contract
# @param version_ Version of this contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):
    registry_address.write(value=registry_address_)
    contract_version.write(value=version_)
    return ()
end

# @notice Function to update withdrawal fee mapping which stores total fee for a user
# @param address_ - address of the user for whom withdrawal fee is to be updated
# @param assetID_ - asset ID of the collateral
# @param fee_to_add_ - withdrawal fee value that is to be added
@external
func update_withdrawal_fee_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address_ : felt, assetID_ : felt, fee_to_add_ : felt
):
    alloc_locals

    # Add authorization for the caller
    
    # Update withdrawal fee mapping of an user
    let current_fee : felt = withdrawal_fee_mapping.read(address=address_, assetID=assetID_)
    let new_fee : felt = current_fee + fee_to_add_
    withdrawal_fee_mapping.write(address=address_, assetID=assetID_, value=new_fee)

    # Update Total withdrawal fee per asset
    let current_total_fee_per_asset : felt = total_withdrawal_fee_per_asset.read(assetID=assetID_)
    let new_total_fee_per_asset : felt = current_total_fee_per_asset + fee_to_add_
    total_withdrawal_fee_per_asset.write(assetID=assetID_, value=new_total_fee_per_asset)

    return ()
end

# @notice Function to get the total accumulated withdrawal fee for a specific user
# @param address_ - address of the user for whom total withdrawal fee is to be obtained
# @param assetID_ - asset ID of the collateral
# @return fee - total accumulated withdrawal fee for the user
@view
func get_user_withdrawal_fee{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address_ : felt, assetID_ : felt
) -> (fee : felt):
    let (fee) = withdrawal_fee_mapping.read(address=address_, assetID=assetID_)
    return (fee)
end

# @notice Function to get the total withdrawal fee accumulated in the system
# @param assetID_ - asset ID of the collateral
# @return fee - total withdrawal fee in the system
@view
func get_total_withdrawal_fee{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt
) -> (fee : felt):
    let (fee) = total_withdrawal_fee_per_asset.read(assetID=assetID_)
    return (fee)
end