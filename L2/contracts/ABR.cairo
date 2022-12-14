%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math import abs_value, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import get_block_timestamp

from contracts.Constants import MasterAdmin_ACTION
from contracts.interfaces.IABR import IABR
from contracts.interfaces.IABRFund import IABRFund
from contracts.interfaces.IMarkets import IMarkets
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import (
    Math64x61_add,
    Math64x61_div,
    Math64x61_fromIntFelt,
    Math64x61_ln,
    Math64x61_mul,
    Math64x61_sqrt,
    Math64x61_sub,
    Math64x61_ONE
)

//############
// Constants #
//############

const NUM_8 = 18446744073709551616;
const HOURS_8 = 28800;

//##########
// Storage #
//##########

// @notice Mapping of marketID to abr value
@storage_var
func abr_value(market_id) -> (abr: felt) {
}

// @notice Mapping of marketID to the timestamp of last updated value
@storage_var
func last_updated(market_id) -> (value: felt) {
}

@storage_var
func base_abr() -> (value: felt) {
}

@storage_var
func bollinger_width() -> (value: felt) {
}

// @notice Stores the last mark price of an asset
@storage_var
func last_mark_price(market_id) -> (price: felt) {
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
    base_abr.write(28823037615171);
    bollinger_width.write(4611686018427387904);
    return ();
}

//#################
// View Functions #
//#################

@view
func get_abr_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt
) -> (abr: felt, price: felt, timestamp: felt) {
    let (abr: felt) = abr_value.read(market_id=market_id_);
    let (price: felt) = last_mark_price.read(market_id=market_id_);
    let (timestamp) = last_updated.read(market_id=market_id_);
    return (abr, price, timestamp);
}

//#####################
// External Functions #
//#####################

@external
func modify_base_abr{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_base_abr_: felt
) {
    with_attr error_message("ABR: Unauthorized") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    base_abr.write(new_base_abr_);

    return ();
}

@external
func modify_bollinger_width{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_bollinger_width_: felt
) {
    with_attr error_message("ABR: Unauthorized") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    bollinger_width.write(new_bollinger_width_);

    return ();
}

// @notice Function to calculate the ABR for the current period
// @param perp_index_len - Size of the perp index prices array
// @param perp_index - Perp index prices array
// @param perp_mark_len - Size of the perp mark prices array
// @param perp_mark - Perp Mark prices array
// @returns res - ABR of the mark & index prices
@external
func calculate_abr{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, perp_index_len: felt, perp_index: felt*, perp_mark_len: felt, perp_mark: felt*
) -> (result: felt) {
    alloc_locals;
    // Get the latest block
    let (block_timestamp) = get_block_timestamp();

    // Fetch the last updated time
    let (last_call) = last_updated.read(market_id=market_id_);

    // Minimum time before the second call
    let min_time = last_call + HOURS_8;
    let is_eight_hours = is_le(block_timestamp, min_time);

    // If 8 hours have not passed yet
    if (is_eight_hours == 1) {
        with_attr error_message("ABR: 8 hours not passed") {
            assert 1 = 0;
        }
    }

    if (perp_mark_len == perp_index_len) {
    } else {
        with_attr error_message("ABR: arguments mismatch") {
            assert 1 = 0;
        }
    }

    // Reduce the array size by factor of 8
    let (index_prices: felt*) = alloc();
    let (mark_prices: felt*) = alloc();
    let (reduced_array_length: felt) = reduce_values(
        market_id_, perp_index_len, perp_index, perp_mark, 0, index_prices, mark_prices, 8, 0, 0, 0
    );

    // Calculate the middle band
    let (avg_array: felt*) = alloc();
    movavg(reduced_array_length, mark_prices, reduced_array_length, mark_prices, 8, avg_array, 0);

    // Calculate the upper & lower band
    let (upper_array: felt*) = alloc();
    let (lower_array: felt*) = alloc();
    let (boll_width: felt) = bollinger_width.read();
    calc_bollinger(
        reduced_array_length,
        upper_array,
        lower_array,
        reduced_array_length,
        mark_prices,
        avg_array,
        8,
        0,
        boll_width,
    );

    // Calculate the diff b/w index and mark
    let (diff: felt*) = alloc();
    calc_diff(reduced_array_length, index_prices, mark_prices, diff, 0);

    // Calculate the premium
    let (ABRdyn: felt*) = alloc();
    movavg(reduced_array_length, diff, reduced_array_length, diff, 8, ABRdyn, 0);

    // Add the jump to the premium price
    let (ABRdyn_jump: felt*) = alloc();
    calc_jump(
        reduced_array_length,
        mark_prices,
        index_prices,
        upper_array,
        lower_array,
        ABRdyn,
        ABRdyn_jump,
        0,
    );

    // # Find the effective ABR rate
    let (base_abr_) = base_abr.read();
    let (rate_sum) = find_abr(reduced_array_length, ABRdyn_jump, 0, base_abr_);

    let (array_size) = Math64x61_fromIntFelt(reduced_array_length);
    let (rate) = Math64x61_div(rate_sum, array_size);

    // Store the result and the timestamp in their storage vars
    let (block_timestamp) = get_block_timestamp();
    abr_value.write(market_id=market_id_, value=rate);
    last_updated.write(market_id=market_id_, value=block_timestamp);

    return (rate,);
}

//#####################
// Internal Functions #
//#####################

// @notice Function to calculate the difference between index and mark prices
// @param array_len_ - Length of the index and mark prices array
// @param index_prices_ - Index prices array
// @param mark_prices_ - Mark prices array
// @param diff_ - Current diff array
// @param iterator_ - Iterator of the array
func calc_diff{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    array_len_: felt, index_prices_: felt*, mark_prices_: felt*, diff_: felt*, iterator_: felt
) {
    // If reached the end of the array, return
    if (array_len_ == 0) {
        return ();
    }

    // Calculate difference between mark and index
    let (diff_sub) = Math64x61_sub([mark_prices_], [index_prices_]);

    // Divide the diff by index price
    let (diff_temp) = Math64x61_div(diff_sub, [index_prices_]);

    // Store it in diff array
    assert diff_[iterator_] = diff_temp;

    // Recursively call the next array element
    return calc_diff(array_len_ - 1, index_prices_ + 1, mark_prices_ + 1, diff_, iterator_ + 1);
}

// @notice Function to calculate the sum of effective abr of a premium array
// @param array_len_ - Length of the array
// @param array_ - Array for which to calculate the abr
// @param sum_ - Current sum of the array
// @param base_abr_ - Base ABR value
// @returns sum - Final sum of the array
func find_abr{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    array_len_: felt, array_: felt*, sum_: felt, base_abr_: felt
) -> (sum: felt) {
    // If reached the end of the array, return
    if (array_len_ == 0) {
        return (sum_,);
    }

    // Calculate the current sum
    let (sum_div) = Math64x61_div([array_], NUM_8);
    let (sum_add) = Math64x61_add(sum_div, base_abr_);
    let (curr_sum) = Math64x61_add(sum_add, sum_);

    // Recursively call the next array element
    return find_abr(array_len_ - 1, array_ + 1, curr_sum, base_abr_);
}

// @notice Function to calculate the sum of a given array window
// @param array_len_ - Length of the array
// @param array_ - Array for which to calculate the sum
// @param window_size_ - Size of the window
// @param sum_ - Current sum of the array
// @returns sum - Final sum of the array
func find_window_sum{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    array_len_: felt, array_: felt*, window_size_: felt, sum_: felt
) -> (sum: felt) {
    // If reached the end of the array, return
    if (window_size_ == 0) {
        return (sum_,);
    }

    // Calculate the current sum
    let (sum_temp) = Math64x61_add(sum_, [array_]);

    // Recursively call the next array element
    return find_window_sum(array_len_, array_ + 1, window_size_ - 1, sum_temp);
}

// @notice Function to calculate the sum of standard deviation
// @param array_len_ - Length of the array
// @param array_ - Array for which to calculate the std
// @param mean_ - Mean of the window
// @param window_size_ - Window size of the array
// @param sum_ - Current sum of the stds
// @returns sum - Final sum of the stds
func find_std_sum{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    array_len_: felt, array_: felt*, mean_: felt, window_size_: felt, sum_: felt
) -> (sum: felt) {
    // If reached the end of the array, return
    if (window_size_ == 0) {
        return (sum_,);
    }

    // Calculates the difference between the array element and the mean
    let (diff) = Math64x61_sub([array_], mean_);

    // Calculates the square root of the difference
    let (diff_sq) = Math64x61_mul(diff, diff);

    // Recursively call the next array element
    return find_std_sum(array_len_, array_ + 1, mean_, window_size_ - 1, sum_ + diff_sq);
}

// @notice Function to calculate the moving average
// @param tail_window_len_ - Length of the tail window array
// @param tail_window_ - Tail window array, start of a window
// @param head_window_len_ - Length of the head window array
// @param head_window_ - Head window array, end of a window
// @param window_size_ - Window size of the array
// @param avg_array_ - Current average array
// @param iterator_- iterator for the arrays
func movavg{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tail_window_len_: felt,
    tail_window_: felt*,
    head_window_len_: felt,
    head_window_: felt*,
    window_size_: felt,
    avg_array_: felt*,
    iterator_: felt,
) {
    alloc_locals;

    // If reached the end of the array, return
    if (head_window_len_ == 0) {
        return ();
    }

    // Check if the iterator is on the left boundary of the window
    let is_boundary = is_le(iterator_, window_size_ - 2);

    if (is_boundary == 1) {
        // Calculate the mean of the window
        let (curr_window_size) = Math64x61_fromIntFelt(iterator_ + 1);
        let (window_sum) = find_window_sum(tail_window_len_, tail_window_, iterator_ + 1, 0);
        let (mean_window) = Math64x61_div(window_sum, curr_window_size);

        // Store the mean in the avg_array
        assert avg_array_[iterator_] = mean_window;

        // Recursively call the next array element
        return movavg(
            tail_window_len_,
            tail_window_,
            head_window_len_ - 1,
            head_window_ + 1,
            window_size_,
            avg_array_,
            iterator_ + 1,
        );
    } else {
        // Calculate the mean of the window
        let (curr_window_size) = Math64x61_fromIntFelt(window_size_);
        let (window_sum) = find_window_sum(tail_window_len_, tail_window_, window_size_, 0);
        let (mean_window) = Math64x61_div(window_sum, curr_window_size);

        // Store the mean in the avg_array
        assert avg_array_[iterator_] = mean_window;

        // Recursively call the next array element
        return movavg(
            tail_window_len_ - 1,
            tail_window_ + 1,
            head_window_len_ - 1,
            head_window_ + 1,
            window_size_,
            avg_array_,
            iterator_ + 1,
        );
    }
}

// @notice Function to calculate the upper and lower bands
// @param array_len_ - Length of upper and lower bands
// @param upper_array_ - Current upper band
// @param lower_array_ - Current lower band
// @param tail_window_len_ - Length of the tail window array
// @param tail_window_ - Tail window array, start of a window
// @param avg_array_ - Average Array
// @param window_size_ - Window size of the array
// @param iterator_ - iterator for the arrays
// @param boll_width_ - Width of the boll band
func calc_bollinger{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    array_len_: felt,
    upper_array_: felt*,
    lower_array_: felt*,
    tail_window_len_: felt,
    tail_window_: felt*,
    avg_array_: felt*,
    window_size_: felt,
    iterator_: felt,
    boll_width_: felt,
) {
    alloc_locals;

    // If reached the end of the array, return
    if (array_len_ == 0) {
        return ();
    }

    local mean = [avg_array_];

    // Check if the iterator is on the left boundary of the window
    let is_boundary = is_le(iterator_, window_size_ - 2);

    if (is_boundary == 1) {
        // Calculate the std deviation of the window
        let (curr_window_size) = Math64x61_fromIntFelt(iterator_ + 1);
        let (std_deviation) = find_std_sum(tail_window_len_, tail_window_, mean, iterator_ + 1, 0);

        local curr_window;
        if (iterator_ == 0) {
            curr_window = 1;
        } else {
            curr_window = curr_window_size - Math64x61_ONE;
        }

        let (std_temp) = Math64x61_div(std_deviation, curr_window);
        let (movstd) = Math64x61_sqrt(std_temp);
        let (movstd_const) = Math64x61_mul(movstd, boll_width_);

        let (lower) = Math64x61_sub(mean, movstd_const);
        let (upper) = Math64x61_add(mean, movstd_const);

        // Store the result in lower and upper band arrays
        assert lower_array_[iterator_] = lower;
        assert upper_array_[iterator_] = upper;

        // Recursively call the next array element
        return calc_bollinger(
            array_len_ - 1,
            upper_array_,
            lower_array_,
            tail_window_len_,
            tail_window_,
            avg_array_ + 1,
            window_size_,
            iterator_ + 1,
            boll_width_,
        );
    } else {
        // Calculate the std deviation of the window
        let (curr_window_size) = Math64x61_fromIntFelt(window_size_);
        let (std_deviation) = find_std_sum(tail_window_len_, tail_window_, mean, window_size_, 0);

        let (curr_size) = Math64x61_sub(curr_window_size, Math64x61_ONE);

        let (std_temp) = Math64x61_div(std_deviation, curr_size);
        let (movstd) = Math64x61_sqrt(std_temp);
        let (movstd_const) = Math64x61_mul(movstd, boll_width_);

        let (lower) = Math64x61_sub(mean, movstd_const);
        let (upper) = Math64x61_add(mean, movstd_const);

        // # Store the result in lower and upper band arrays
        assert lower_array_[iterator_] = lower;
        assert upper_array_[iterator_] = upper;

        // # Recursively call the next array element
        return calc_bollinger(
            array_len_ - 1,
            upper_array_,
            lower_array_,
            tail_window_len_ - 1,
            tail_window_ + 1,
            avg_array_ + 1,
            window_size_,
            iterator_ + 1,
            boll_width_,
        );
    }
}

// @notice Function to calculate the jump and ABRdyn
// @param array_len_ - Size of the mark prices and index prices array
// @param mark_prices_ - Mark prices array
// @param index_prices_ - Index prices array
// @param upper_array_ -  Upper band array
// @param lower_array_ - Lower band array
// @param ABRdyn_ - ABRdyn populated array
// @param ABRdyn_jump_ - Current ABRdyn array
// @param iterator_ - iterator for the arrays
func calc_jump{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    array_len_: felt,
    mark_prices_: felt*,
    index_prices_: felt*,
    upper_array_: felt*,
    lower_array_: felt*,
    ABRdyn_: felt*,
    ABRdyn_jump_: felt*,
    iterator_: felt,
) {
    alloc_locals;

    // If reached the end of the array, return
    if (array_len_ == 0) {
        return ();
    }

    // Calculate the diffrence between bands and the mark prices
    let (upper_diff) = Math64x61_sub([mark_prices_], [upper_array_]);
    let (lower_diff) = Math64x61_sub([lower_array_], [mark_prices_]);

    // Check if the upper or lower diff is positive
    let is_upper = is_le(upper_diff, 0);
    let is_lower = is_le(lower_diff, 0);

    local jump_value_upper;
    local jump_value_lower;

    // If the upper_diff is zero
    if (is_upper == 1) {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        jump_value_upper = 0;
    } else {
        // Calculate jump
        let (ln_jump) = Math64x61_ln(upper_diff);
        let is_jump_negative = is_le(ln_jump, 0);

        // Add the jump to the premium
        if (is_jump_negative == 0) {
            let (jump) = Math64x61_div(ln_jump, [index_prices_]);
            jump_value_upper = jump;
        } else {
            jump_value_upper = 0;
        }

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    tempvar syscall_ptr = syscall_ptr;
    tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
    tempvar range_check_ptr = range_check_ptr;

    // If the lower_diff is non-negative
    if (is_lower == 1) {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        jump_value_lower = 0;
    } else {
        // Calculate jump
        let (ln_jump) = Math64x61_ln(lower_diff);
        let is_jump_negative = is_le(ln_jump, 0);

        // Add the jump to the premium
        if (is_jump_negative == 0) {
            let (jump) = Math64x61_div(ln_jump, [index_prices_]);
            jump_value_lower = jump;
        } else {
            jump_value_lower = 0;
        }

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    let (temp_jump) = Math64x61_add([ABRdyn_], jump_value_upper);
    let (total_jump) = Math64x61_sub(temp_jump, jump_value_lower);
    assert ABRdyn_jump_[iterator_] = total_jump;

    // Recursively call the next array element
    return calc_jump(
        array_len_ - 1,
        mark_prices_ + 1,
        index_prices_ + 1,
        upper_array_ + 1,
        lower_array_ + 1,
        ABRdyn_ + 1,
        ABRdyn_jump_,
        iterator_ + 1,
    );
}

// @notice Function to reduce the values from 480 -> 60
// @param market_id_ - Market ID of the pair
// @param perp_iterator_ - Iterator for perp_index and perp_mark arrays
// @param perp_index_ -  Perp Index prices array
// @param perp_mark_ - Perp Mark prices array
// @param reduced_iterator_ - Iterator for index_prices and mark_prices arrays
// @param index_prices_ - Current index prices array
// @param mark_prices_ -  Current mark prices array
// @param window_ - Size of the window (Not a sliding window mean)
// @param window_iterator_ - Iterator for the window
// @param index_sum_ - Stores the current sum of the index array
// @param mark_sum_ - Stores the current sum of the mark array
// @returns reduced_iterator - New length of the array
func reduce_values{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt,
    perp_iterator_: felt,
    perp_index_: felt*,
    perp_mark_: felt*,
    reduced_iterator_: felt,
    index_prices_: felt*,
    mark_prices_: felt*,
    window_: felt,
    window_iterator_: felt,
    index_sum_: felt,
    mark_sum_: felt,
) -> (reduced_iterator: felt) {
    alloc_locals;

    // Store the last price in last_mark_price variable
    if (perp_iterator_ == 1) {
        last_mark_price.write(market_id=market_id_, value=[perp_mark_]);
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // If reached the end of the array, return
    if (perp_iterator_ == 0) {
        return (reduced_iterator_,);
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Add the index and mark prices to their respective sums
    let (curr_index_sum) = Math64x61_add(index_sum_, [perp_index_]);
    let (curr_mark_sum) = Math64x61_add(mark_sum_, [perp_mark_]);

    // If the iterator reaches the window
    if (window_iterator_ == window_ - 1) {
        // Calculate the 64x61 value of the window
        let (window_size) = Math64x61_fromIntFelt(window_);

        // Calculate the mean value of index and mark prices
        let (index_mean) = Math64x61_div(curr_index_sum, window_size);
        let (mark_mean) = Math64x61_div(curr_mark_sum, window_size);

        // Store the value in index and mark arrays
        assert index_prices_[reduced_iterator_] = index_mean;
        assert mark_prices_[reduced_iterator_] = mark_mean;

        // Recursively call the next array element
        return reduce_values(
            market_id_,
            perp_iterator_ - 1,
            perp_index_ + 1,
            perp_mark_ + 1,
            reduced_iterator_ + 1,
            index_prices_,
            mark_prices_,
            window_,
            0,
            0,
            0,
        );
    } else {
        // Recursively call the next array element
        return reduce_values(
            market_id_,
            perp_iterator_ - 1,
            perp_index_ + 1,
            perp_mark_ + 1,
            reduced_iterator_,
            index_prices_,
            mark_prices_,
            window_,
            window_iterator_ + 1,
            curr_index_sum,
            curr_mark_sum,
        );
    }
}
