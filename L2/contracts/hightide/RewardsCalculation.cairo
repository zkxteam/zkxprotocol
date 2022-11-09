%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_not_zero

from contracts.DataTypes import XpValues, TradingSeason
from starkware.starknet.common.syscalls import get_caller_address
from contracts.libraries.CommonLibrary import CommonLib, get_contract_version, get_registry_address
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHighTide import IHighTide
from contracts.Constants import Hightide_INDEX, VALIDATOR_ROUTER_INDEX

// This stores the block numbers set by the Nodes
@storage_var
func block_number_array(index: felt) -> (res: felt) {
}

// This stores the length of the block_number_array
@storage_var
func block_number_array_len() -> (res: felt) {
}

// This stores the starting index of block_number_array where the block numbers are stored for that season
// season_id -> staring_block_number
@storage_var
func block_number_start(season_id: felt) -> (res: felt) {
}

// Stores the Xp value for a user for that season
@storage_var
func xp_value(season_id, user_address: felt) -> (res: felt) {
}

// //////////////
// Constructor //
// //////////////

// @notice Constructor of the smart-contract
// @param registry_address Address of the AuthorizedRegistry contract
// @param version Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address: felt, version: felt
) {
    CommonLib.initialize(registry_address, version);
    return ();
}

// ///////
// View //
// ///////

// @notice This function is used to get block numbers in a season
// @param season_id_ - Season id for which to return block numbers
// @returns block_numbers_len - Length of the final block_numbers array
// @returns block_numbers - Array of the block_numbers
@view
func get_block_numbers{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) -> (block_numbers_len: felt, block_numbers: felt*) {
    with_attr error_message("RewardsCalculation: Invalid season_id") {
        assert_lt(0, season_id_);
    }

    // Get starting index
    let (starting_index: felt) = block_number_start.read(season_id=season_id_);

    // Initialize an array
    let (block_numbers: felt*) = alloc();

    if (starting_index == 0) {
        return (0, block_numbers);
    }

    // Get the starting index of the next season_id (if it's not set, it returns 0)
    let (ending_index: felt) = block_number_start.read(season_id=season_id_ + 1);

    // Recursively fill the array and return it
    return get_block_number_recurse(block_numbers, starting_index, ending_index, 0);
}

// @notice This function is gets the xp value for a user in a season
// @param season_id_ - id of the season
// @param user_address_ - Address of the user
// @param xp_value - Xp value for that user in the required season
@view
func get_user_xp_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, user_address_: felt
) -> (xp_value: felt) {
    with_attr error_message("RewardsCalculation: Invalid user_address") {
        assert_not_zero(user_address_);
    }

    with_attr error_message("RewardsCalculation: Invalid season_id") {
        assert_lt(0, season_id_);
    }

    let (xp_value_user: felt) = xp_value.read(season_id=season_id_, user_address=user_address_);

    return (xp_value_user,);
}
// ///////////
// Internal //
// ///////////

// @notice This function is called by get_block_numbers
// @param block_numbers_ - Array of populated block numbers
// @param current_index_ - Index at which the block number is currently pointing to
// @param ending_index_ - Index at which to stop
// @param iterator_ - Stores the current length of the populated array
// @param xp_values_ - Array of XpValues struct
// @returns block_numbers_len - Length of the final block_numbers array
// @returns block_numbers - Array of the block_numbers
func get_block_number_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    block_numbers_: felt*, current_index_: felt, ending_index_: felt, iterator_: felt
) -> (block_numbers_len: felt, block_numbers: felt*) {
    // Return condition 1, return if we reach the starting index of the next season_id
    if (current_index_ == ending_index_) {
        return (iterator_, block_numbers_);
    }

    let (current_block_number: felt) = block_number_array.read(index=current_index_);

    // Return condition 2, return if we reach an index where the blocknumber is not set
    if (current_block_number == 0) {
        return (iterator_, block_numbers_);
    }

    // Set the blocknumber in our array
    assert block_numbers_[iterator_] = current_block_number;

    // Recursively call the next index
    return get_block_number_recurse(
        block_numbers_=block_numbers_,
        current_index_=current_index_ + 1,
        ending_index_=ending_index_,
        iterator_=iterator_ + 1,
    );
}

// @notice This function is called by set_user_xp_values
// @param season_id_ - id of the season
// @param xp_values_len_ - Length of the xp array
// @param xp_values_ - Array of XpValues struct
func set_user_xp_values_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, xp_values_len_: felt, xp_values_: XpValues*
) {
    alloc_locals;
    // Termination conditon
    if (xp_values_len_ == 0) {
        return ();
    }

    // Validate the input
    with_attr error_message("RewardsCalculation: Xp value cannot be <= 0") {
        assert_le(0, [xp_values_].final_xp_value);
    }

    if ([xp_values_].user_address == 0) {
        with_attr error_message("RewardsCalculation: User Address cannot be 0") {
            assert 1 = 0;
        }
    }

    // Range check

    let (current_xp_value: felt) = xp_value.read(
        season_id=season_id_, user_address=[xp_values_].user_address
    );

    // Check if the xp value is already set
    with_attr error_message("RewardsCalculation: Xp value already ser") {
        assert current_xp_value = 0;
    }
    // Write the value
    xp_value.write(
        season_id=season_id_,
        user_address=[xp_values_].user_address,
        value=[xp_values_].final_xp_value,
    );

    return set_user_xp_values_recurse(
        season_id_=season_id_,
        xp_values_len_=xp_values_len_ - 1,
        xp_values_=xp_values_ + XpValues.SIZE,
    );
}

// ///////////
// External //
// ///////////

// @notice This function is used to record final xp values for users
// @param season_id_ - id of the season
// @param xp_values_len - Length of the xp array
// @param xp_values - Array of XpValues struct
@external
func set_user_xp_values{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, xp_values_len: felt, xp_values: XpValues*
) {
    // Auth Check
    let (registry) = get_registry_address();
    let (version) = get_contract_version();

    let (caller) = get_caller_address();

    // Get Hightide address from Authorized Registry
    let (validator_router) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=VALIDATOR_ROUTER_INDEX, version=version
    );

    with_attr error_message("RewardsCalculation: Unauthorized call") {
        assert caller = validator_router;
    }

    set_user_xp_values_recurse(season_id_, xp_values_len, xp_values);
    return ();
}

// @notice This function is used to record blocknumbers that'll be used for calculating xp
// @param block_number_ - Block number to be set
@external
func set_block_number{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    block_number_: felt
) {
    // Auth check
    let (registry) = get_registry_address();
    let (version) = get_contract_version();

    let (caller) = get_caller_address();

    // Get Hightide address from Authorized Registry
    let (validator_router) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=VALIDATOR_ROUTER_INDEX, version=version
    );

    with_attr error_message("RewardsCalculation: Unauthorized call") {
        assert caller = validator_router;
    }

    // Get Hightide address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get trading season data
    let (season_id: felt) = IHighTide.get_current_season_id(contract_address=hightide_address);

    with_attr error_message("RewardsCalculations: No ongoing season") {
        assert_not_zero(season_id);
    }

    // Get the starting index of the season
    let (season_starting_index: felt) = block_number_start.read(season_id=season_id);

    // Get the current length of the array
    let (current_array_len: felt) = block_number_array_len.read();

    // If it's a new season, initialize the starting index
    if (season_starting_index == 0) {
        if (season_id == 1) {
            // Set the starting index for the new season
            block_number_start.write(season_id=season_id, value=1);

            // Write the new block number
            block_number_array.write(index=1, value=block_number_);

            // Update the length of the array
            block_number_array_len.write(1);
        } else {
            // Set the starting index for the new season
            block_number_start.write(season_id=season_id, value=current_array_len + 1);

            // Write the new block number
            block_number_array.write(index=current_array_len + 1, value=block_number_);

            // Update the length of the array
            block_number_array_len.write(current_array_len + 1);
        }
    } else {
        // Write the new block number
        block_number_array.write(index=current_array_len + 1, value=block_number_);

        // Update the length of the array
        block_number_array_len.write(current_array_len + 1);
    }

    return ();
}
