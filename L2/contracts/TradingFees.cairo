%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_nn, assert_not_zero
from starkware.cairo.common.math_cmp import is_le, is_nn

from contracts.Constants import FeeDiscount_INDEX, ManageFeeDetails_ACTION
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IFeeDiscount import IFeeDiscount
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_assert64x61, Math64x61_mul, Math64x61_ONE

//##########
// Structs #
//##########

// Struct to store base fee percentage for each tier for maker and taker
struct BaseFee {
    numberOfTokens: felt,
    makerFee: felt,
    takerFee: felt,
}

// Struct to store discount percentage for each tier
struct Discount {
    numberOfTokens: felt,
    discount: felt,
}

//#########
// Events #
//#########

// Event emitted whenever update_base_fees() is called
@event
func update_base_fees_called(tier: felt, fee_details: BaseFee) {
}

// Event emitted whenever update_discount() is called
@event
func update_discount_called(tier: felt, discount_details: Discount) {
}

//##########
// Storage #
//##########

// Stores the maximum base fee tier
@storage_var
func max_base_fee_tier() -> (value: felt) {
}

// Stores the maximum discount tier
@storage_var
func max_discount_tier() -> (value: felt) {
}

// Stores base fee percentage for each tier for maker and tker
@storage_var
func base_fee_tiers(tier: felt) -> (value: BaseFee) {
}

// Stores discount percentage for each tier
@storage_var
func discount_tiers(tier: felt) -> (value: Discount) {
}

//##############
// Constructor #
//##############

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    return ();
}

//#################
// View Functions #
//#################

// @notice Getter function for base fees
// @param tier_ - tier level
// @returns base_fee - BaseFee struct for the tier
@view
func get_base_fees{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tier_: felt
) -> (base_fee: BaseFee) {
    let (base_fee) = base_fee_tiers.read(tier=tier_);
    return (base_fee,);
}

// @notice Getter function for discount
// @param tier_ - tier level
// @returns base_fee - Discount struct for the tier
@view
func get_discount{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(tier_: felt) -> (
    discount: Discount
) {
    let (discount) = discount_tiers.read(tier=tier_);
    return (discount,);
}

// @notice Getter function for max base fee tier
// @returns value - Max base fee tier
@view
func get_max_base_fee_tier{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    value: felt
) {
    let (value) = max_base_fee_tier.read();
    return (value,);
}

// @notice Getter function for max discount tier
// @returns value - Max discount tier
@view
func get_max_discount_tier{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    value: felt
) {
    let (value) = max_discount_tier.read();
    return (value,);
}

// @notice Function which returns discount for a user
// @param address_ - address of the user
// @param side_ - 0 if maker, 1 if taker
// @returns base_fee - base fee for the user
// @returns discount - discount for the user
@view
func get_user_fee_and_discount{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address_: felt, side_: felt
) -> (fee: felt) {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (fee_discount_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=FeeDiscount_INDEX, version=version
    );
    let (number_of_tokens) = IFeeDiscount.get_user_tokens(
        contract_address=fee_discount_address, address=address_
    );

    let (max_base_fee_level) = max_base_fee_tier.read();
    let (base_fee_maker, base_fee_taker) = find_user_base_fee(
        number_of_tokens_=number_of_tokens, tier_=max_base_fee_level
    );

    let (max_discount_level) = max_discount_tier.read();
    let (discount) = find_user_discount(
        number_of_tokens_=number_of_tokens, tier_=max_discount_level
    );

    local base_fee;
    if (side_ == 0) {
        base_fee = base_fee_maker;
    } else {
        base_fee = base_fee_taker;
    }

    // Calculate fee after the discount
    let non_discount = Math64x61_ONE - discount;
    let fee: felt = Math64x61_mul(base_fee, non_discount);

    return (fee=fee);
}

//#####################
// External Functions #
//#####################

// @notice Function to update base fee details
// @param tier_ - fee tier
// @param fee_details - base fee for the current tier
@external
func update_base_fees{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tier_: felt, fee_details: BaseFee
) {
    alloc_locals;
    // Auth check
    with_attr error_message("Caller is not authorized to manage fee details") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, ManageFeeDetails_ACTION);
    }

    with_attr error_message("Tier and fee details values cannot be negative") {
        assert_nn(tier_);
        assert_not_zero(tier_);
        assert_nn(fee_details.numberOfTokens);
        assert_nn(fee_details.makerFee);
        assert_nn(fee_details.takerFee);
    }

    with_attr error_message("Maker fee and taker fee values should be in 64x61 representation") {
        Math64x61_assert64x61(fee_details.makerFee);
        Math64x61_assert64x61(fee_details.takerFee);
    }

    let (current_max_base_fee_tier) = max_base_fee_tier.read();

    with_attr error_message(
            "Tier should be less than or equal to (current max base fee tier + 1)") {
        assert_le(tier_, current_max_base_fee_tier + 1);
    }

    // Verify whether the base fee of the tier being updated/added is correct
    // with respect to the lower tier, if lower tier exists
    let (lower_tier_fee) = base_fee_tiers.read(tier=tier_ - 1);
    if (tier_ - 1 != 0) {
        with_attr error_message("New fee details are not valid with respect to lower tier") {
            assert_lt(lower_tier_fee.numberOfTokens, fee_details.numberOfTokens);
            assert_lt(fee_details.makerFee, lower_tier_fee.makerFee);
            assert_lt(fee_details.takerFee, lower_tier_fee.takerFee);
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Verify whether the base fee of the tier being updated/added is correct
    // with respect to the upper tier, if upper tier exists
    let (upper_tier_fee) = base_fee_tiers.read(tier=tier_ + 1);
    let is_max_base_fee_tier = is_le(current_max_base_fee_tier, tier_);
    if (is_max_base_fee_tier != 1) {
        with_attr error_message("New fee details are not valid with respect to upper tier") {
            assert_lt(fee_details.numberOfTokens, upper_tier_fee.numberOfTokens);
            assert_lt(upper_tier_fee.makerFee, fee_details.makerFee);
            assert_lt(upper_tier_fee.takerFee, fee_details.takerFee);
        }
        base_fee_tiers.write(tier=tier_, value=fee_details);
    } else {
        max_base_fee_tier.write(value=tier_);
        base_fee_tiers.write(tier=tier_, value=fee_details);
    }

    // update_base_fees_called event is emitted
    update_base_fees_called.emit(tier=tier_, fee_details=fee_details);

    return ();
}

// @notice Function to update discount details
// @param tier - Level of Tier to modify
// @param tier_criteria_- Dicsount for the current tier
@external
func update_discount{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tier_: felt, discount_details: Discount
) {
    alloc_locals;
    // Auth check
    with_attr error_message("Caller is not authorized to manage fee details") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, ManageFeeDetails_ACTION);
    }

    with_attr error_message("Tier and discount details values cannot be negative") {
        assert_nn(tier_);
        assert_not_zero(tier_);
        assert_nn(discount_details.numberOfTokens);
        assert_nn(discount_details.discount);
    }

    with_attr error_message("Discount should be in 64x61 representation") {
        Math64x61_assert64x61(discount_details.discount);
    }

    let (current_max_discount_tier) = max_discount_tier.read();

    with_attr error_message(
            "Tier should be less than or equal to (current max base fee tier + 1)") {
        assert_le(tier_, current_max_discount_tier + 1);
    }

    // Verify whether the discount of the tier being updated/added is correct
    // with respect to the lower tier, if lower tier exists
    let (lower_tier_discount) = discount_tiers.read(tier=tier_ - 1);
    if (tier_ - 1 != 0) {
        with_attr error_message("New discount details are not valid with respect to lower tier") {
            assert_lt(lower_tier_discount.numberOfTokens, discount_details.numberOfTokens);
            assert_lt(lower_tier_discount.discount, discount_details.discount);
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Verify whether the discount of the tier being updated/added is correct
    // with respect to the upper tier, if upper tier exists
    let (upper_tier_discount) = discount_tiers.read(tier=tier_ + 1);
    let is_max_discount_tier = is_le(current_max_discount_tier, tier_);
    if (is_max_discount_tier != 1) {
        with_attr error_message("New discount details are not valid with respect to upper tier") {
            assert_lt(discount_details.numberOfTokens, upper_tier_discount.numberOfTokens);
            assert_lt(discount_details.discount, upper_tier_discount.discount);
        }
        discount_tiers.write(tier=tier_, value=discount_details);
    } else {
        max_discount_tier.write(value=tier_);
        discount_tiers.write(tier=tier_, value=discount_details);
    }

    // update_discount_called event is emitted
    update_discount_called.emit(tier=tier_, discount_details=discount_details);

    return ();
}

//#####################
// Internal Functions #
//#####################

// @notice Recursive funtion to find the base fee tier of the user
// @param  number_of_tokens_ - number of the tokens of the user
// @param tier_ - tier level
// @returns base_fee_maker - base fee for the maker for the tier
// @returns base_fee_maker - base fee for the taker for the tier
func find_user_base_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    number_of_tokens_: felt, tier_: felt
) -> (base_fee_maker: felt, base_fee_taker: felt) {
    alloc_locals;
    let (fee_details) = base_fee_tiers.read(tier=tier_);
    let sub_result = number_of_tokens_ - fee_details.numberOfTokens;
    let result = is_nn(sub_result);
    if (result == 1) {
        return (base_fee_maker=fee_details.makerFee, base_fee_taker=fee_details.takerFee);
    } else {
        return find_user_base_fee(number_of_tokens_, tier_ - 1);
    }
}

// @notice Recursive funtion to find the discount tier of the user
// @param  number_of_tokens_ - number of the tokens of the user
// @param tier_ - tier level
// @returns discount - discount for the tier
func find_user_discount{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    number_of_tokens_: felt, tier_: felt
) -> (discount: felt) {
    alloc_locals;
    let (discount_details) = discount_tiers.read(tier=tier_);
    let sub_result = number_of_tokens_ - discount_details.numberOfTokens;
    let result = is_nn(sub_result);
    if (result == 1) {
        return (discount=discount_details.discount);
    } else {
        return find_user_discount(number_of_tokens_, tier_ - 1);
    }
}
