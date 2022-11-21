%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import get_block_timestamp

from contracts.Constants import Hightide_INDEX, ManageHighTide_ACTION
from contracts.DataTypes import LeaderboardStat
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHighTide import IHighTide
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority

// /////////
// Events //
// /////////

// Event emitted whenever collateral is transferred from account by trading
@event
func leaderboard_update(season_id: felt, pair_id: felt, epoch: felt, timestamp: felt) {
}

// Event emitted whenever the number_of_traders variable is changed
@event
func number_of_top_traders_update(old_value: felt, new_value: felt) {
}

// Event emitted whenever the time_between_calls variable is changed
@event
func time_between_calls_update(old_value: felt, new_value: felt) {
}

// //////////
// Storage //
// //////////

// This stores the leaderboard data in a mapping
@storage_var
func leaderboard_mapping(season_id: felt, pair_id: felt, epoch: felt, index: felt) -> (
    value: LeaderboardStat
) {
}

// Stores the number of epochs
@storage_var
func epoch_length(season_id: felt) -> (length: felt) {
}

// This stores the mapping from an epoch to its timestamp
@storage_var
func epoch_mapping(season_id: felt, epoch: felt) -> (timestamp: felt) {
}

// Stores the number of traders that must be stored in an epoch
@storage_var
func number_of_top_traders() -> (res: felt) {
}

// Stores the time interval after which the next call is to be made
@storage_var
func time_between_calls() -> (res: felt) {
}

// Stores the timestamp at which the last call was made
@storage_var
func last_call_timestamp(season_id: felt) -> (timestamp: felt) {
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

@view
func get_next_call{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    remaining_seconds: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get trading season data
    let (season_id: felt) = IHighTide.get_current_season_id(contract_address=hightide_address);

    // If there is no active season, return -1
    if (season_id == 0) {
        return (-1,);
    }

    // Get the last timestamp recorded
    let (current_last_call_timestamp: felt) = last_call_timestamp.read(season_id=season_id);

    // If it's the first call
    if (current_last_call_timestamp == 0) {
        return (0,);
    } else {
        // get current block timestamp
        let (current_timestamp) = get_block_timestamp();
        let (current_time_between_calls: felt) = time_between_calls.read();

        // get next timestamp when the call must be made
        let next_call_timestamp = current_last_call_timestamp + current_time_between_calls;

        // Time between now and next_call
        let remaining_time = next_call_timestamp - current_timestamp;

        // Check if the call is delayed i.e the remaining time is negative
        let is_delayed = is_le(remaining_time, 0);

        // If it's delayed return 0
        if (is_delayed == 1) {
            return (0,);
            // Else return remaining time
        } else {
            return (remaining_time,);
        }
    }
}

// @dev status - 1 => Call pending (Can make a call rn)
// @dev status - 0 => Cool down period (Can't make a call rn)
@view
func get_call_status{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    status: felt
) {
    let (get_remaining_time: felt) = get_next_call();
    if (get_remaining_time == 0) {
        return (1,);
    } else {
        return (0,);
    }
}

// ///////////
// External //
// ///////////
@external
func set_time_between_calls{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_time_between_calls: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("Leaderboard: Unauthorized call") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }

    // Check to see if the value is positive and not 0
    with_attr error_message("Leaderboard: Invalid time_between_calls provided") {
        assert_lt(0, new_time_between_calls);
    }

    // Get the current value of the variable
    let (current_time_between_calls: felt) = time_between_calls.read();

    // Emit the update event
    time_between_calls_update.emit(
        old_value=current_time_between_calls, new_value=new_time_between_calls
    );

    // Write the new value
    time_between_calls.write(value=new_time_between_calls);

    return ();
}

@external
func set_number_of_top_traders{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_number_of_top_traders: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("Leaderboard: Unauthorized call") {
        verify_caller_authority(registry, version, ManageHighTide_ACTION);
    }

    // Check to see if the value is positive and not 0
    with_attr error_message("Leaderboard: Invalid number_of_traders provided") {
        assert_le(0, new_number_of_top_traders);
    }

    // Get the current value of the variable
    let (current_number_of_top_traders: felt) = number_of_top_traders.read();

    // Emit the update event
    number_of_top_traders_update.emit(
        old_value=current_number_of_top_traders, new_value=new_number_of_top_traders
    );

    // Write the new value
    number_of_top_traders.write(value=new_number_of_top_traders);
    return ();
}

@external
func set_leaderboard{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    pair_id_: felt, leaderboard_array_len: felt, leaderboard_array: LeaderboardStat*
) -> (res: felt) {
    alloc_locals;
    // Get status
    let (status: felt) = get_call_status();

    // If it's not time yet, return -1
    with_attr error_message("Leaderboard: Cool down period") {
        assert_not_zero(status);
    }

    let (number_of_entries: felt) = number_of_top_traders.read();

    // The length of the array should be same as number_of_top_traders variable
    with_attr error_message("Leaderboard: Invalid number of entries") {
        assert leaderboard_array_len = number_of_entries;
    }

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (hightide_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Get trading season id
    let (season_id: felt) = IHighTide.get_current_season_id(contract_address=hightide_address);

    // Get current epoch
    let (current_epoch: felt) = epoch_length.read(season_id=season_id);

    // Get current timestamp
    let (current_timestamp: felt) = get_block_timestamp();

    // Update the epoch mapping
    epoch_mapping.write(season_id=season_id, epoch=current_epoch, value=current_timestamp);

    // Recursively write the leaderboard stats to state
    set_leaderboard_recurse(
        leaderboard_array_len_=leaderboard_array_len,
        leaderboard_array_=leaderboard_array,
        season_id_=season_id,
        pair_id_=pair_id_,
        epoch_=current_epoch,
        iterator_=0,
    );

    // Update the length of the epoch
    epoch_length.write(season_id=season_id, value=current_epoch + 1);

    // Update the last called timestamp
    last_call_timestamp.write(season_id=season_id, value=current_timestamp);

    leaderboard_update.emit(
        season_id=season_id, pair_id=pair_id_, epoch=current_epoch, timestamp=current_timestamp
    );
    return (1,);
}

// ///////////
// Internal //
// ///////////

func set_leaderboard_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    leaderboard_array_len_: felt,
    leaderboard_array_: LeaderboardStat*,
    season_id_: felt,
    pair_id_: felt,
    epoch_: felt,
    iterator_: felt,
) {
    // Exit condition
    if (iterator_ == leaderboard_array_len_) {
        return ();
    }

    with_attr error_message("Leaderboard: Invalid reward provided") {
        assert_le(0, [leaderboard_array_].reward);
    }

    // Write to leaderboard mapping
    leaderboard_mapping.write(
        season_id=season_id_,
        pair_id=pair_id_,
        epoch=epoch_,
        index=iterator_,
        value=[leaderboard_array_],
    );

    // Set the next value
    return set_leaderboard_recurse(
        leaderboard_array_len_=leaderboard_array_len_,
        leaderboard_array_=leaderboard_array_ + LeaderboardStat.SIZE,
        season_id_=season_id_,
        pair_id_=pair_id_,
        epoch_=epoch_,
        iterator_=iterator_ + 1,
    );
}
