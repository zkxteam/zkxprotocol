%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_nn, assert_not_zero
from starkware.cairo.common.math_cmp import is_le

from contracts.DataTypes import XpValue
from starkware.starknet.common.syscalls import (
    deploy,
    get_block_number,
    get_block_timestamp,
    get_caller_address,
)
from starkware.cairo.common.uint256 import Uint256, uint256_add, uint256_lt

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

@view
func get_block_numbers{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) {
    with_attr error_message("RewardsCalculation: Invalid season_id") {
        assert_lt(0, season_id_);
    }

    // Get starting index
    let (starting_index: felt) = block_number_start.read(season_id=season_id_);
    with_attr error_message("RewardsCalculation: No blocknumbers set for this season") {
        assert_not_zero(starting_index);
    }

    // Initialize an array
    let (block_numbers: felt*) = alloc();

    // Get the starting index of the next season_id (if it's not set, it returns 0)
    let (ending_index: felt) = block_number_start.read(season_id=season_id_ + 1);

    // Recursively fill the array and return it
    return get_block_number_recurse(block_numbers, starting_index, ending_index, 0);
}

@view
func get_user_xp_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, user_address_: felt
) {
    with_attr error_message("RewardsCalculation: Invalid user_address") {
        assert_not_zero(user_address);
    }

    with_attr error_message("RewardsCalculation: Invalid season_id") {
        assert_lt(0, season_id_);
    }

    let (xp_value_user: felt) = xp_value.read(season_id=season_id_, user_address=user_address_);

    return (xp_value_user);
}
// ///////////
// Internal //
// ///////////

func get_block_number_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    block_numbers: felt*, current_index: felt, ending_index: felt, iterator: felt
) {
    // Return condition 1, return if we reach the starting index of the next season_id
    if (current_index == ending_index) {
        return (iterator, block_numbers);
    }

    let (current_block_number: felt) = block_number_array.read(index=current_index);

    // Return condition 2, return if we reach an index where the blocknumber is not set
    if (current_block_number == 0) {
        return (iterator, block_numbers);
    }

    // Set the blocknumber in our array
    assert block_numbers[iterator] = current_block_number;

    // Recursively call the next index
    return get_block_number_recurse(
        block_numbers=block_numbers,
        current_index=current_index + 1,
        ending_index=ending_index,
        iterator=iterator + 1,
    );
}

func set_user_xp_values_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt, xp_values_len: felt, xp_values: XpValues*
) {
    // Termination conditon
    if (xp_values_len == 0) {
        return ();
    }

    // Validate the input
    with_attr error_message("Xp value cannot be <= 0") {
        assert_lt(0, [xp_values].xp_value);
    }

    if ([xp_values].user_address == 0) {
        with_attr error_message("User Address cannot be 0") {
            assert 1 = 0;
        }
    }

    // Range check

    // Write the value
    xp_value.write(
        season_id=season_id, user_address=[xp_values].user_address, value=[xp_values].xp_value
    );

    return set_user_xp_values_recurse(
        season_id=season_id, xp_values_len=xp_values_len - 1, xp_values=xp_values + XpValues.SIZE
    );
}

// ///////////
// External //
// ///////////

@external
func set_user_xp_values{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt, xp_values_len: felt, xp_values: XpValues*
) {
    // Auth Check
    set_user_xp_values_recurse(season_id, xp_values_len, xp_values, 0);
    return ();
}

@external
func set_block_number{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    block_number_: felt
) {
    // Auth check
    let (registry) = get_registry_address();
    let (version) = get_contract_version();

    // Get Hightide address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get trading season data
    let (season_id: TradingSeason) = IHighTide.get_current_season_id(
        contract_address=hightide_address
    );

    // Get the starting index of the season
    let (season_starting_index: felt) = block_number_start.read(season_id=season_id);

    // Get the current length of the array
    let (current_array_len: felt) = block_number_array_len.read();

    // If it's a new season, initialize the starting index
    if (season_starting_index == 0) {
        if (season_id == 1) {
            block_number_start.write(season_id=season_id, value=1);

            // Write the new block number
            block_number_array.write(index=1, value=block_number_);

            // Update the length of the array
            block_number_array_len.write(1);
        } else {
            block_number_start.write(season_id=season_id, value=current_array_len);

            // Write the new block number
            block_number_array.write(index=current_array_len, value=block_number_);

            // Update the length of the array
            block_number_array_len.write(current_array_len + 1);
        }
    } else {
        // Write the new block number
        block_number_array.write(index=current_array_len, value=block_number_);

        // Update the length of the array
        block_number_array_len.write(current_array_len + 1);
    }

    return ();
}
