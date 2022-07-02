%lang starknet

%builtins pedersen range_check ecdsa

from contracts.Constants import AccountRegistry_INDEX
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero

#
# Storage
#

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
func withdrawal_fee_mapping(user_l2_address : felt, collateral_id : felt) -> (fee : felt):
end

# @notice Stores the total withdrawal fee per asset
@storage_var
func total_withdrawal_fee_per_asset(collateral_id : felt) -> (accumulated_fee : felt):
end

#
# Constructor
#

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

#
# Getters
#

# @notice Function to get the total accumulated withdrawal fee for a specific user
# @param user_l2_address_ - address of the user for whom total withdrawal fee is to be obtained
# @param collateral_id_ - collateral to be withdrawn
# @return fee - total accumulated withdrawal fee for the user
@view
func get_user_withdrawal_fee{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    user_l2_address_ : felt, collateral_id_ : felt
) -> (fee : felt):
    let (fee) = withdrawal_fee_mapping.read(user_l2_address=user_l2_address_, collateral_id=collateral_id_)
    return (fee)
end

# @notice Function to get the total withdrawal fee accumulated in the system
# @param collateral_id_ - collateral to be withdrawn
# @return fee - total withdrawal fee in the system
@view
func get_total_withdrawal_fee{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    collateral_id_ : felt
) -> (fee : felt):
    let (fee) = total_withdrawal_fee_per_asset.read(collateral_id=collateral_id_)
    return (fee)
end

#
# Business Logic
#

# @notice Function to update withdrawal fee mapping which stores total fee for a user
# @param user_l2_address_ - address of the user for whom withdrawal fee is to be updated
# @param collateral_id_ - collateral to be withdrawn
# @param fee_to_add_ - withdrawal fee value that is to be added
@external
func update_withdrawal_fee_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    user_l2_address_ : felt, collateral_id_ : felt, fee_to_add_ : felt
):
    alloc_locals

    # # Auth check
    # let (registry) = registry_address.read()
    # let (version) = contract_version.read()
    # let (caller) = get_caller_address()

    # # fetch account registry contract address
    # let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
    #     contract_address=registry, index=AccountRegistry_INDEX, version=version
    # )
    # # check whether caller is registered user
    # let (present) = IAccountRegistry.is_registered_user(
    #     contract_address=account_registry_address, address_=caller
    # )

    # with_attr error_message("Called account contract is not registered"):
    #     assert_not_zero(present)
    # end
    
    # Update withdrawal fee mapping of an user
    let current_fee : felt = withdrawal_fee_mapping.read(user_l2_address=user_l2_address_, collateral_id=collateral_id_)
    let new_fee : felt = current_fee + fee_to_add_
    withdrawal_fee_mapping.write(user_l2_address=user_l2_address_, collateral_id=collateral_id_, value=new_fee)

    # Update Total withdrawal fee per asset
    let current_total_fee_per_asset : felt = total_withdrawal_fee_per_asset.read(collateral_id=collateral_id_)
    let new_total_fee_per_asset : felt = current_total_fee_per_asset + fee_to_add_
    total_withdrawal_fee_per_asset.write(collateral_id=collateral_id_, value=new_total_fee_per_asset)

    return ()
end