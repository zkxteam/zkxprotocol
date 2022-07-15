%lang starknet

from contracts.Constants import (
    FeeDiscount_INDEX,
    ManageFeeDetails_ACTION
)
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IFeeDiscount import IFeeDiscount
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.cairo.common.math_cmp import is_le, is_nn
from contracts.Math_64x61 import Math64x61_mul
from contracts.libraries.Utils import verify_caller_authority

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of Authorized Registry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# @notice Stores the maximum base fee tier
@storage_var
func max_base_fee_tier() -> (value : felt):
end

# @notice Stores the maximum discount tier
@storage_var
func max_discount_tier() -> (value : felt):
end

# @notice Struct to store base fee percentage for each tier for maker and taker
struct BaseFee:
    member numberOfTokens : felt
    member makerFee : felt
    member takerFee : felt
end

# @notice Struct to store discount percentage for each tier
struct Discount:
    member numberOfTokens : felt
    member discount : felt
end

# @notice Stores base fee percentage for each tier for maker and tker
@storage_var
func base_fee_tiers(tier : felt) -> (value : BaseFee):
end

# @notice Stores discount percentage for each tier
@storage_var
func discount_tiers(tier : felt) -> (value : Discount):
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

# @notice Function to update base fee details
# @param tier_ - fee tier
# @param fee_details - base fee for the current tier
@external
func update_base_fees{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_ : felt, fee_details : BaseFee
):
    # Auth check
    with_attr error_message("Caller is not authorized to manage fee details"):
        let (registry) = registry_address.read()
        let (version) = contract_version.read()
        verify_caller_authority(registry, version, ManageFeeDetails_ACTION)
    end

    # Update max base fee tier if new tier is the biggest
    let (current_max_base_fee_tier) = max_base_fee_tier.read()
    let (result) = is_le(current_max_base_fee_tier, tier_)
    if result == 1:
        max_base_fee_tier.write(value=tier_)
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    # Update the fees
    base_fee_tiers.write(tier=tier_, value=fee_details)
    return ()
end

# @notice Function to update discount details
# @param tier - Level of Tier to modify
# @param tier_criteria_- Dicsount for the current tier
@external
func update_discount{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_ : felt, discount_details : Discount
):
    # Auth check
    with_attr error_message("Caller is not authorized to manage fee details"):
        let (registry) = registry_address.read()
        let (version) = contract_version.read()
        verify_caller_authority(registry, version, ManageFeeDetails_ACTION)
    end

    # Update max discount tier if new tier is the biggest
    let (current_max_discount_tier) = max_discount_tier.read()
    let (result) = is_le(current_max_discount_tier, tier_)
    if result == 1:
        max_discount_tier.write(value=tier_)
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    # Update the discount
    discount_tiers.write(tier=tier_, value=discount_details)
    return ()
end

# @notice Function to modify max base fee tier
# @param tier_ - value for max base fee tier
@external
func update_max_base_fee_tier{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_ : felt
):
    # Auth check
    with_attr error_message("Caller is not authorized to manage fee details"):
        let (registry) = registry_address.read()
        let (version) = contract_version.read()
        verify_caller_authority(registry, version, ManageFeeDetails_ACTION)
    end

    max_base_fee_tier.write(value=tier_)
    return ()
end

# @notice Function to modify max discount tier
# @param tier_ - value for max discount tier
@external
func update_max_discount_tier{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_ : felt
):
    # Auth check
    with_attr error_message("Caller is not authorized to manage fee details"):
        let (registry) = registry_address.read()
        let (version) = contract_version.read()
        verify_caller_authority(registry, version, ManageFeeDetails_ACTION)
    end

    max_discount_tier.write(value=tier_)
    return ()
end

# @notice Getter function for base fees
# @param tier_ - tier level
# @returns base_fee - BaseFee struct for the tier
@view
func get_base_fees{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_ : felt
) -> (base_fee : BaseFee):
    let (base_fee) = base_fee_tiers.read(tier=tier_)
    return (base_fee)
end

# @notice Getter function for discount
# @param tier_ - tier level
# @returns base_fee - Discount struct for the tier
@view
func get_discount{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_ : felt
) -> (discount : Discount):
    let (discount) = discount_tiers.read(tier=tier_)
    return (discount)
end

# @notice Getter function for max base fee tier
# @returns value - Max base fee tier
@view
func get_max_base_fee_tier{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    value : felt
):
    let (value) = max_base_fee_tier.read()
    return (value)
end

# @notice Getter function for max discount tier
# @returns value - Max discount tier
@view
func get_max_discount_tier{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    value : felt
):
    let (value) = max_discount_tier.read()
    return (value)
end

# @notice Recursive funtion to find the base fee tier of the user
# @param  number_of_tokens_ - number of the tokens of the user
# @param tier_ - tier level
# @returns base_fee_maker - base fee for the maker for the tier
# @returns base_fee_maker - base fee for the taker for the tier
func find_user_base_fee{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    number_of_tokens_ : felt, tier_ : felt
) -> (base_fee_maker : felt, base_fee_taker : felt):
    alloc_locals
    let (fee_details) = base_fee_tiers.read(tier=tier_)
    let sub_result = number_of_tokens_ - fee_details.numberOfTokens
    let (result) = is_nn(sub_result)
    if result == 1:
        return (base_fee_maker=fee_details.makerFee, base_fee_taker=fee_details.takerFee)
    else:
        return find_user_base_fee(number_of_tokens_, tier_ - 1)
    end
end

# @notice Recursive funtion to find the discount tier of the user
# @param  number_of_tokens_ - number of the tokens of the user
# @param tier_ - tier level
# @returns discount - discount for the tier
func find_user_discount{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    number_of_tokens_ : felt, tier_ : felt
) -> (discount : felt):
    alloc_locals
    let (discount_details) = discount_tiers.read(tier=tier_)
    let sub_result = number_of_tokens_ - discount_details.numberOfTokens
    let (result) = is_nn(sub_result)
    if result == 1:
        return (discount=discount_details.discount)
    else:
        return find_user_discount(number_of_tokens_, tier_ - 1)
    end
end

# @notice Function which returns discount for a user
# @param address_ - address of the user
# @param side_ - 0 if maker, 1 if taker
# @returns base_fee - base fee for the user
# @returns discount - discount for the user
@view
func get_user_fee_and_discount{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address_ : felt, side_ : felt
) -> (fee : felt):
    alloc_locals
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (fee_discount_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=FeeDiscount_INDEX, version=version
    )
    let (number_of_tokens) = IFeeDiscount.get_user_tokens(
        contract_address=fee_discount_address, address=address_
    )

    let (max_base_fee_level) = max_base_fee_tier.read()
    let (base_fee_maker, base_fee_taker) = find_user_base_fee(
        number_of_tokens_=number_of_tokens, tier_=max_base_fee_level
    )

    let (max_discount_level) = max_discount_tier.read()
    let (discount) = find_user_discount(
        number_of_tokens_=number_of_tokens, tier_=max_discount_level
    )

    local base_fee
    if side_ == 0:
        base_fee = base_fee_maker
    else:
        base_fee = base_fee_taker
    end

    # Calculate fee after the discount
    let non_discount = 2305843009213693952 - discount
    let fee : felt = Math64x61_mul(base_fee, non_discount)

    return (fee=fee)
end