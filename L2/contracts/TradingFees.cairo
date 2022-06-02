%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.cairo.common.math_cmp import is_le, is_nn
from starkware.starknet.common.syscalls import get_caller_address

# @notice Stores the address of AdminAuth contract
@storage_var
func auth_address() -> (contract_address : felt):
end

# @notice Stores the address of FeeDiscount contract
@storage_var
func fee_discount_address() -> (contract_address : felt):
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

# @notice Constructor for the smart-contract
# @param auth_address_ - Address of the AdminAuth Contract
# @param fee_discount_address_ - Address of the FeeDiscount Contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    auth_address_ : felt, fee_discount_address_ : felt
):
    auth_address.write(value=auth_address_)
    fee_discount_address.write(value=fee_discount_address_)
    return ()
end

# @notice Function to update base fee details
# @param tier_ - fee tier
# @param fee_details - base fee for the current tier
@external
func update_base_fees{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_ : felt, fee_details : BaseFee
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=4
    )
    assert_not_zero(access)

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
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=4
    )
    assert_not_zero(access)

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
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=4
    )
    assert_not_zero(access)

    max_base_fee_tier.write(value=tier_)
    return ()
end

# @notice Function to modify max discount tier
# @param tier_ - value for max discount tier
@external
func update_max_discount_tier{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_ : felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=4
    )
    assert_not_zero(access)

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
) -> (base_fee : felt, discount : felt):
    alloc_locals
    let (fee_discount_addr) = fee_discount_address.read()
    let (number_of_tokens) = IFeeDiscount.get_user_tokens(
        contract_address=fee_discount_addr, address=address_
    )

    let (max_base_fee_level) = max_base_fee_tier.read()
    let (base_fee_maker, base_fee_taker) = find_user_base_fee(
        number_of_tokens_=number_of_tokens, tier_=max_base_fee_level
    )

    let (max_discount_level) = max_discount_tier.read()
    let (discount) = find_user_discount(
        number_of_tokens_=number_of_tokens, tier_=max_discount_level
    )

    if side_ == 0:
        return (base_fee=base_fee_maker, discount=discount)
    else:
        return (base_fee=base_fee_taker, discount=discount)
    end
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end

# @notice FeeDiscount interface
@contract_interface
namespace IFeeDiscount:
    func get_user_tokens(address : felt) -> (value : felt):
    end
end
