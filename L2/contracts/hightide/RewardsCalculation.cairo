%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import (
    assert_in_range,
    assert_le,
    assert_lt,
    assert_not_zero,
    unsigned_div_rem,
)
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import get_block_number, get_caller_address

from contracts.Constants import Hightide_INDEX, ManageHighTide_ACTION
from contracts.DataTypes import TradingSeason, XpValues
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHighTide import IHighTide
from contracts.libraries.CommonLibrary import CommonLib, get_contract_version, get_registry_address
from contracts.libraries.Utils import verify_caller_authority

// /////////
// Events //
// /////////

// Event emitted whenever collateral is transferred from account by trading
@event
func block_number_set(season_id: felt, block_number: felt) {
}

// Event emitted whenever collateral is transferred to account by trading
@event
func xp_value_set(season_id: felt, user_address: felt, xp_value: felt) {
}

// //////////
// Storage //
// //////////

// This stores the block numbers set by the Nodes
@storage_var
func block_number_array(season_id: felt, index: felt) -> (res: felt) {
}

// This stores the length of the block_number_array
@storage_var
func block_number_array_len(season_id: felt) -> (res: felt) {
}

// Stores the Xp value for a user for that season
@storage_var
func xp_value(season_id, user_address: felt) -> (res: felt) {
}

// Stores block number interval
@storage_var
func block_interval() -> (res: felt) {
}

// Stores current season's block number up to which values were set
@storage_var
func season_last_block_number(season_id: felt) -> (res: felt) {
}

// //////////////
// Constructor //
// //////////////

// @notice Constructor of the smart-contract
// @param registry_address_ - Address of the AuthorizedRegistry contract
// @param version_ - Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    return ();
}

// ///////
// View //
// ///////

// @notice Function to get block number range within which node needs to select a random block number
// @param season_id_ - season id for which block range is to be obtained
// @return start_block - starting block number range (inclusive)
// @return end_block - ending block number range (inclusive) (both values will be 0, if no more values to be set)
@view
func get_block_range{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) -> (start_block: felt, end_block: felt) {
    alloc_locals;
    local smaller_block_number;

    let (current_block_interval) = block_interval.read();
    with_attr error_message("RewardsCalculation: Block interval is not set") {
        assert_lt(0, current_block_interval);
    }

    let (registry) = get_registry_address();
    let (version) = get_contract_version();

    // Get Hightide address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Verify whether the season id exists
    IHighTide.verify_season_id_exists(contract_address=hightide_address, season_id_=season_id_);

    // Get current season's starting block number
    let (season) = IHighTide.get_season(contract_address=hightide_address, season_id=season_id_);

    let (last_block_number) = season_last_block_number.read(season_id_);

    if (last_block_number == 0) {
        let start_block_number = season.start_block_number;

        return (start_block_number, start_block_number + current_block_interval - 1);
    }

    // Find the smaller block number between season end block number and current block number
    let (current_block_number) = get_block_number();
    if (season.end_block_number != 0) {
        if (is_le(current_block_number, season.end_block_number) == TRUE) {
            smaller_block_number = current_block_number;
        } else {
            smaller_block_number = season.end_block_number;
        }
        tempvar range_check_ptr = range_check_ptr;
    } else {
        smaller_block_number = current_block_number;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Check whether if we add block interval to last block number it goes beyond
    // current block number or season end block number
    if (is_le(last_block_number + current_block_interval, smaller_block_number) == TRUE) {
        if (is_le(last_block_number + 1, last_block_number + current_block_interval) == TRUE) {
            return (last_block_number + 1, last_block_number + current_block_interval);
        } else {
            return (0, 0);
        }
    } else {
        if (is_le(last_block_number + 1, smaller_block_number) == TRUE) {
            return (last_block_number + 1, smaller_block_number);
        } else {
            return (0, 0);
        }
    }
}

// @notice This function is used to get block numbers in a season
// @param season_id_ - Season id for which to return block numbers
// @return block_numbers_len - Length of the final block_numbers array
// @return block_numbers - Array of the block_numbers
@view
func get_block_numbers{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt
) -> (block_numbers_len: felt, block_numbers: felt*) {
    alloc_locals;

    with_attr error_message("RewardsCalculation: Invalid season_id") {
        assert_lt(0, season_id_);
    }

    let (registry) = get_registry_address();
    let (version) = get_contract_version();

    // Verify whether season id is valid
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );
    IHighTide.verify_season_id_exists(contract_address=hightide_address, season_id_=season_id_);

    // Initialize an array
    let (block_numbers: felt*) = alloc();

    let (current_array_len: felt) = block_number_array_len.read(season_id_);

    // Recursively fill the array and return it
    let (block_numbers_len: felt) = get_block_number_recurse(
        season_id_, block_numbers, 0, current_array_len
    );

    return (block_numbers_len, block_numbers);
}

// @notice This function is gets the xp value for a user in a season
// @param season_id_ - id of the season
// @param user_address_ - Address of the user
// @return xp_value - Xp value for that user in the required season
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
// External //
// ///////////

// @notice Function to set block interval by admin
// block_interval_ - block interval value to be set
@external
func set_block_interval{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    block_interval_: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("RewardsCalculation: Unauthorized call to set block number") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }

    with_attr error_message("RewardsCalculation: Block interval should be more than 0") {
        assert_lt(0, block_interval_);
    }

    block_interval.write(block_interval_);

    return ();
}

// @notice This function is used to record final xp values for users
// @param season_id_ - id of the season
// @param xp_values_len - Length of the xp array
// @param xp_values - Array of XpValues struct
@external
func set_user_xp_values{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, xp_values_len: felt, xp_values: XpValues*
) {
    alloc_locals;
    let (registry) = get_registry_address();
    let (version) = get_contract_version();

    // Get Hightide address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    let (is_expired: felt) = IHighTide.get_season_expiry_state(
        contract_address=hightide_address, season_id=season_id_
    );

    // Revert if season is still ongoing
    with_attr error_message("RewardsCalculation: Season still ongoing") {
        assert is_expired = TRUE;
    }

    // Recursively update the users' xp value
    set_user_xp_values_recurse(season_id_, xp_values_len, xp_values);
    return ();
}

// @notice This function is used to record blocknumbers that'll be used for calculating xp
// @param season_id_ - season id for which block number needs to be set
// @param block_number_ - Block number to be set
@external
func set_block_number{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, block_number_: felt
) {
    alloc_locals;
    let (registry) = get_registry_address();
    let (version) = get_contract_version();

    // Get Hightide address from Authorized Registry
    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Verify whether season id exists
    IHighTide.verify_season_id_exists(contract_address=hightide_address, season_id_=season_id_);

    // Verify whether the block number is valid
    let (start_block, end_block) = get_block_range(season_id_);
    with_attr error_message("RewardsCalculations: Block number is not in range") {
        assert_in_range(block_number_, start_block, end_block + 1);
    }

    // Get the current length of the array
    let (current_array_len: felt) = block_number_array_len.read(season_id_);

    block_number_array.write(season_id_, current_array_len, block_number_);
    block_number_array_len.write(season_id_, current_array_len + 1);
    season_last_block_number.write(season_id_, end_block);

    block_number_set.emit(season_id=season_id_, block_number=block_number_);

    return ();
}

// ///////////
// Internal //
// ///////////

// @notice This function is called by get_block_numbers
// @param season_id_ - season id for which block numbers need to be fetched
// @param block_numbers_ - Array of populated block numbers
// @param iterator_ - Stores the current length of the populated array
// @param len_ - length of the block number array for this season
// @return block_numbers_len - Length of the final block_numbers array
func get_block_number_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, block_numbers_: felt*, iterator_: felt, len_: felt
) -> (block_numbers_len: felt) {
    if (iterator_ == len_) {
        return (iterator_,);
    }

    let (current_block_number: felt) = block_number_array.read(season_id_, iterator_);

    // Set the blocknumber in our array
    assert block_numbers_[iterator_] = current_block_number;

    // Recursively call the next index
    return get_block_number_recurse(
        season_id_=season_id_, block_numbers_=block_numbers_, iterator_=iterator_ + 1, len_=len_
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

    with_attr error_message("RewardsCalculation: User Address cannot be 0") {
        assert_not_zero([xp_values_].user_address);
    }

    let (current_xp_value: felt) = xp_value.read(
        season_id=season_id_, user_address=[xp_values_].user_address
    );

    // Check if the xp value is already set
    with_attr error_message("RewardsCalculation: Xp value already set") {
        assert current_xp_value = 0;
    }
    // Write the value
    xp_value.write(
        season_id=season_id_,
        user_address=[xp_values_].user_address,
        value=[xp_values_].final_xp_value,
    );

    xp_value_set.emit(
        season_id=season_id_,
        user_address=[xp_values_].user_address,
        xp_value=[xp_values_].final_xp_value,
    );

    return set_user_xp_values_recurse(
        season_id_=season_id_,
        xp_values_len_=xp_values_len_ - 1,
        xp_values_=xp_values_ + XpValues.SIZE,
    );
}
