%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.common.syscalls import (
    get_contract_address,
    call_contract,
    get_caller_address,
    get_tx_signature,
)
from starkware.cairo.common.math import (
    assert_not_zero,
    assert_nn,
    assert_le,
    assert_in_range,
    assert_lt,
)
from starkware.cairo.common.math import abs_value
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math_cmp import is_le
from contracts.Math_64x61 import (
    Math64x61_add,
    Math64x61_sub,
    Math64x61_mul,
    Math64x61_div,
    Math64x61_fromFelt,
    Math64x61_sqrt,
    Math64x61_ln,
)

const NUM_STD = 4611686018427387904
const NUM_1 = 2305843009213693952

#################
@storage_var
func sum_total() -> (res : felt):
end

@storage_var
func mean_64() -> (res : felt):
end

@view
func return_total{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (total) = sum_total.read()
    return (total)
end

@view
func return_mean64{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (total) = mean_64.read()
    return (total)
end
################

# @notice Function to calculate the difference between index and mark prices
# @param index_prices_len - Size of the index prices array
# @param index_prices - Index prices array
# @param mark_prices_len - Size of the mark prices array
# @param mark_prices - Mark prices array
# @param diff_len - Length of the diff array
# @param diff - Empty diff array
# @returns diff_len - Length of the diff array
# @returns diff - The updated diff array
func calc_diff{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    index_prices_len : felt,
    index_prices : felt*,
    mark_prices_len : felt,
    mark_prices : felt*,
    diff_len : felt,
    diff : felt*,
    iterator,
) -> (diff_len : felt, diff : felt*):
    # If reached the end of the array, return
    if index_prices_len == 0:
        return (diff_len, diff)
    end

    # Calculate difference between mark and index
    let (diff_sub) = Math64x61_sub([mark_prices], [index_prices])

    # Divide the diff by index price
    let (diff_temp) = Math64x61_div(diff_sub, [index_prices])

    # Store it in diff array
    assert diff[iterator] = diff_temp

    # Recursively call the next array element
    return calc_diff(
        index_prices_len - 1,
        index_prices + 1,
        mark_prices_len - 1,
        mark_prices + 1,
        diff_len + 1,
        diff,
        iterator + 1,
    )
end

# @notice Function to calculate the sum of a given array
# @param array_len - Length of the array
# @param array - Array for which to calculate the sum
# @param sum - Sum of the array
# @returns sum - Final sum of the array
func find_sum{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    array_len : felt, array : felt*, sum : felt
) -> (sum : felt):
    alloc_locals

    # If reached the end of the array, return
    if array_len == 0:
        return (sum)
    end

    # Calculate the current sum
    let (sum_temp) = Math64x61_add(sum, [array])

    # Recursively call the next array element
    return find_sum(array_len - 1, array + 1, sum_temp)
end

# @notice Function to calculate the sum of a given array window
# @param array_len - Length of the array
# @param array - Array for which to calculate the sum
# @param window_size - Size of the window
# @param sum - Sum of the array
# @returns sum - Final sum of the array
func find_window_sum{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    array_len : felt, array : felt*, window_size : felt, sum : felt
) -> (sum : felt):
    alloc_locals

    # If reached the end of the array, return
    if window_size == 0:
        return (sum)
    end

    # Calculate the current sum
    let (sum_temp) = Math64x61_add(sum, [array])

    # Recursively call the next array element
    return find_window_sum(array_len, array + 1, window_size - 1, sum_temp)
end

# @notice Function to calculate the standard deviation
# @param array_len - Length of the array
# @param array - Array for which to calculate the std
# @param mean - Mean of the window
# @param window_size - Window size of the array
# @param sum - Sum of the stds
# @returns sum - Final sum of the stds
func find_std{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    array_len : felt, array : felt*, mean : felt, window_size : felt, sum : felt
) -> (sum : felt):
    alloc_locals

    # If reached the end of the array, return
    if window_size == 0:
        return (sum)
    end

    # Calculates the difference between the array element and the mean
    let (diff) = Math64x61_sub([array], mean)

    # Calculates the square root of the difference
    let (diff_sq) = Math64x61_mul(diff, diff)

    # Recursively call the next array element
    return find_std(array_len, array + 1, mean, window_size - 1, sum + diff_sq)
end

# @notice Function to calculate the moving average
# @param tail_window_len - Length of the tail window array
# @param tail_window - Tail window array, start of a window
# @param head_window_len - Length of the head window array
# @param head_window - Head window array, end of a window
# @param window_size - Window size of the array
# @param avg_array_size - Length of the average array
# @param avg_array - Average Array
# @param iterator - iterator for the arrays
# @returns avg_array_size - Length of the average array
# @returns avg_array - Average Array
func movavg{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tail_window_len : felt,
    tail_window : felt*,
    head_window_len : felt,
    head_window : felt*,
    window_size : felt,
    avg_array_size : felt,
    avg_array : felt*,
    iterator : felt,
) -> (avg_array_size : felt, avg_array : felt*):
    alloc_locals

    # If reached the end of the array, return
    if head_window_len == 0:
        return (iterator, avg_array)
    end

    # Check if the iterator is on the left boundary of the window
    let (is_boundary) = is_le(iterator, window_size - 2)

    if is_boundary == 1:
        # Calculate the mean of the window
        let (curr_window_size) = Math64x61_fromFelt(iterator + 1)
        let (window_sum) = find_window_sum(tail_window_len, tail_window, iterator + 1, 0)
        let (mean_window) = Math64x61_div(window_sum, curr_window_size)

        # Store the mean in the avg_array
        assert avg_array[iterator] = mean_window

        # Recursively call the next array element
        return movavg(
            tail_window_len,
            tail_window,
            head_window_len - 1,
            head_window + 1,
            window_size,
            avg_array_size + 1,
            avg_array,
            iterator + 1,
        )
    else:
        # Calculate the mean of the window
        let (curr_window_size) = Math64x61_fromFelt(window_size)
        let (window_sum) = find_window_sum(tail_window_len, tail_window, window_size, 0)
        let (mean_window) = Math64x61_div(window_sum, curr_window_size)

        # Store the mean in the avg_array
        assert avg_array[iterator] = mean_window

        # Recursively call the next array element
        return movavg(
            tail_window_len - 1,
            tail_window + 1,
            head_window_len - 1,
            head_window + 1,
            window_size,
            avg_array_size + 1,
            avg_array,
            iterator + 1,
        )
    end
end

# @notice Function to calculate the upper and lower bands
# @param upper_array_len - Length of the upper band
# @param upper_array - Empty Upper band
# @param lower_array_len - Length of the lower band
# @param lower_array - Empty Upper band
# @param tail_window_len - Length of the tail window array
# @param tail_window - Tail window array, start of a window
# @param avg_array_len - Length of the average array
# @param avg_array - Average Array
# @param window_size - Window size of the array
# @param iterator - iterator for the arrays
# @returns upper_array_len - Length of the upper band
# @returns upper_array - Empty Upper band
# @returns lower_array_len - Length of the lower band
# @returns lower_array - Empty Upper band
func calc_bollinger{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    upper_array_len : felt,
    upper_array : felt*,
    lower_array_len : felt,
    lower_array : felt*,
    tail_window_len : felt,
    tail_window : felt*,
    avg_array_len : felt,
    avg_array : felt*,
    window_size : felt,
    iterator : felt,
) -> (upper_array_len : felt, upper_array : felt*, lower_array_len : felt, lower_array : felt*):
    alloc_locals

    # If reached the end of the array, return
    if avg_array_len == 0:
        return (iterator, upper_array, iterator, lower_array)
    end

    local mean = [avg_array]

    # Check if the iterator is on the left boundary of the window
    let (is_boundary) = is_le(iterator, window_size - 2)

    if is_boundary == 1:
        # Calculate the std deviation of the window
        let (curr_window_size) = Math64x61_fromFelt(iterator + 1)
        let (std_deviation) = find_std(tail_window_len, tail_window, mean, iterator + 1, 0)

        local curr_window
        if iterator == 0:
            curr_window = 1
        else:
            curr_window = curr_window_size - NUM_1
        end

        let (std_temp) = Math64x61_div(std_deviation, curr_window)
        let (movstd) = Math64x61_sqrt(std_temp)
        let (movstd_const) = Math64x61_mul(movstd, NUM_STD)

        let (lower) = Math64x61_sub(mean, movstd_const)
        let (upper) = Math64x61_add(mean, movstd_const)

        # Store the result in lower and upper band arrays
        assert lower_array[iterator] = lower
        assert upper_array[iterator] = upper

        # Recursively call the next array element
        return calc_bollinger(
            upper_array_len + 1,
            upper_array,
            lower_array_len + 1,
            lower_array,
            tail_window_len,
            tail_window,
            avg_array_len - 1,
            avg_array + 1,
            window_size,
            iterator + 1,
        )
    else:
        # Calculate the std deviation of the window
        let (curr_window_size) = Math64x61_fromFelt(window_size)
        let (std_deviation) = find_std(tail_window_len, tail_window, mean, window_size, 0)

        let curr_size = curr_window_size - NUM_1

        let (std_temp) = Math64x61_div(std_deviation, curr_size)
        let (movstd) = Math64x61_sqrt(std_temp)
        let (movstd_const) = Math64x61_mul(movstd, NUM_STD)

        let (lower) = Math64x61_sub(mean, movstd_const)
        let (upper) = Math64x61_add(mean, movstd_const)

        # Store the result in lower and upper band arrays
        assert lower_array[iterator] = lower
        assert upper_array[iterator] = upper

        # Recursively call the next array element
        return calc_bollinger(
            upper_array_len + 1,
            upper_array,
            lower_array_len + 1,
            lower_array,
            tail_window_len - 1,
            tail_window + 1,
            avg_array_len - 1,
            avg_array + 1,
            window_size,
            iterator + 1,
        )
    end
end

# @notice Function to calculate the jump and ABRdyn
# @param mark_prices_len - Size of the mark prices array
# @param mark_prices - Mark prices array
# @param index_prices_len - Size of the index prices array
# @param index_prices - Index prices array
# @param upper_array_len - Length of the upper band
# @param upper_array - Empty Upper band
# @param lower_array_len - Length of the lower band
# @param lower_array - Empty Upper band
# @param ABRdyn_len - Length of the ABR array
# @param ABRdyn - ABRdyn array
# @param iterator - iterator for the arrays
func calc_jump{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    mark_prices_len : felt,
    mark_prices : felt*,
    index_prices_len : felt,
    index_prices : felt*,
    upper_array_len : felt,
    upper_array : felt*,
    lower_array_len : felt,
    lower_array : felt*,
    ABRdyn_len : felt,
    ABRdyn : felt*,
    iterator : felt,
) -> (ABRdyn_len : felt, ABRdyn : felt*):
    alloc_locals

    # If reached the end of the array, return
    if mark_prices_len == 0:
        return (ABRdyn_len, ABRdyn)
    end

    # Calculate the diffrence between bands and the mark prices
    let (upper_diff) = Math64x61_sub([mark_prices], [upper_array])
    let (lower_diff) = Math64x61_sub([lower_array], [mark_prices])

    # Check if the upper or lower diff is positive
    let (is_upper) = is_le(upper_diff, 0)
    let (is_lower) = is_le(lower_diff, 0)

    # If the upper_diff is non-negative
    if is_upper == 0:
        # Calculate jump
        let (jump_) = Math64x61_div(upper_diff, [index_prices])
        let (ln_jump_) = Math64x61_ln(jump_)

        # Add the jump to the premium
        assert ABRdyn[iterator] = [ABRdyn] + ln_jump_

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    # If the lower_diff is non-negative
    if is_lower == 0:
        # Calculate jump
        let (jump_) = Math64x61_div(lower_diff, [index_prices])
        let (ln_jump_) = Math64x61_ln(jump_)

        # Add the jump to the premium
        assert ABRdyn[iterator] = [ABRdyn] - ln_jump_

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    # Recursively call the next array element
    return calc_jump(
        mark_prices_len - 1,
        mark_prices + 1,
        index_prices_len - 1,
        index_prices + 1,
        upper_array_len - 1,
        upper_array + 1,
        lower_array_len - 1,
        lower_array + 1,
        ABRdyn_len,
        ABRdyn,
        iterator + 1,
    )
end

# @notice Function to calculate the ABR for the current period
# @param index_prices_len - Size of the index prices array
# @param index_prices - Index prices array
# @param mark_prices_len - Size of the mark prices array
# @param mark_prices - Mark prices array
# @returns res - ABR of the mark & index prices
@external
func calculate_abr{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    index_prices_len : felt, index_prices : felt*, mark_prices_len : felt, mark_prices : felt*
) -> (
    upper_jump_len : felt,
    upper_jump : felt*,
    lower_jump_len : felt,
    lower_jump : felt*,
    ABRdyn_len : felt,
    ABRdyn : felt*,
):
    alloc_locals

    # Calculate the middle band
    let (avg_array : felt*) = alloc()
    let (avg_array_len : felt, avg_array : felt*) = movavg(
        mark_prices_len, mark_prices, mark_prices_len, mark_prices, 3, 0, avg_array, 0
    )

    # Calculate the upper & lower band
    let (upper_array : felt*) = alloc()
    let (lower_array : felt*) = alloc()

    let (upper_array_len, upper_array, lower_array_len, lower_array) = calc_bollinger(
        0, upper_array, 0, lower_array, mark_prices_len, mark_prices, avg_array_len, avg_array, 3, 0
    )

    # Calculate the diff b/w index and mark
    let (diff : felt*) = alloc()
    let (diff_len : felt, diff : felt*) = calc_diff(
        index_prices_len, index_prices, mark_prices_len, mark_prices, 0, diff, 0
    )

    # Calculate the premium
    let (ABRdyn : felt*) = alloc()
    let (ABRdyn_len : felt, ABRdyn : felt*) = movavg(
        diff_len, diff, diff_len, diff, 3, 0, ABRdyn, 0
    )

    # # Add the jump to the premium price
    # let (upper_jump_len, upper_jump, lower_jump_len, lower_jump, ABRdyn_len, ABRdyn) =

    return calc_jump(
        mark_prices_len,
        mark_prices,
        index_prices_len,
        index_prices,
        upper_array_len,
        upper_array,
        lower_array_len,
        lower_array,
        ABRdyn_len,
        ABRdyn,
        0,
    )

    # # Find the effective ABR rate
    # let (rate_sum) = find_sum(ABRdyn_len, ABRdyn, 0)
    # let (rate) = Math64x61_div(rate_sum, ABRdyn_len)
    # return (rate)
end
