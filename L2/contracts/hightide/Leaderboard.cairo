%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_not_zero, unsigned_div_rem

from contracts.Constants import Hightide_INDEX
from contracts.DataTypes import TradingSeason
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHighTide import IHighTide
from contracts.libraries.CommonLibrary import CommonLib, get_contract_version, get_registry_address

// /////////
// Events //
// /////////

// Event emitted whenever collateral is transferred from account by trading
@event
func leaderboard_update(season_id: felt, epoch: felt, timestamp: felt) {
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
func leaderboard_mapping(season_id: felt, epoch: felt, index) -> (value: felt) {
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
    // Get trading season data
    let (season_id: felt) = IHighTide.get_current_season_id(contract_address=hightide_address);

    // If there is no active season, return -1
    if (season_id == 0) {
        return -1;
    }

    // Get the last timestamp recorded
    let (last_call_timestamp: felt) = last_call_timestamp.read(season_id=season_id);

    // If it's the first call
    if (last_call_timestamp == 0) {
        return 0;
    } else {
        // get current block timestamp
        let (local current_timestamp) = get_block_timestamp();
        let (time_between_calls: felt) = time_between_calls.read();

        // get next timestamp when the call must be made
        let next_call_timestamp = last_call_timestamp + time_between_calls;

        // Time between now and next_call
        let remaining_time = next_call_timestamp - current_timestamp;

        // Check if the call is delayed i.e the remaining time is negative
        let (is_delayed: felt) = is_lt(remaining_time, 0);

        // If it's delayed return 0
        if (is_delayed == 1) {
            return 0;
            // Else return remaining time
        } else {
            return remaining_time;
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
        return 1;
    } else {
        return 0;
    }
}
