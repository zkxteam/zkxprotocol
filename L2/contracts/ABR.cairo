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
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.hash_state import hash_init, hash_finalize, hash_update
from contracts.Math_64x61 import (
    Math64x61_add,
    Math64x61_sub,
    Math64x61_mul,
    Math64x61_div,
    Math64x61_fromFelt,
    Math64x61_sqrt,
)

const NUM_STD = 4611686018427387904
const NUM_1 = 2305843009213693952

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

func calc_diff{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    index_prices_len : felt,
    index_prices : felt*,
    mark_prices_len : felt,
    mark_prices : felt*,
    diff_len : felt,
    diff : felt*,
    iterator,
) -> (diff_len : felt, diff : felt*):
    if index_prices_len == 0:
        return (diff_len, diff)
    end

    let (diff_sub) = Math64x61_sub([mark_prices], [index_prices])
    let (diff_temp) = Math64x61_div(diff_sub, [index_prices])

    assert diff[iterator] = diff_temp

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

func find_sum{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    array_len : felt, array : felt*, window_size : felt, sum : felt
) -> (sum : felt):
    alloc_locals
    if window_size == 0:
        sum_total.write(sum)
        return (sum)
    end

    let (sum_temp) = Math64x61_add(sum, [array])

    return find_sum(array_len, array + 1, window_size - 1, sum_temp)
end

func find_std{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    array_len : felt, array : felt*, mean : felt, window_size : felt, sum : felt
) -> (sum : felt):
    alloc_locals
    if window_size == 0:
        return (sum)
    end

    let (diff) = Math64x61_sub([array], mean)
    let (diff_sq) = Math64x61_mul(diff, diff)

    return find_std(array_len, array + 1, mean, window_size - 1, sum + diff_sq)
end

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

    if head_window_len == 0:
        return (iterator, avg_array)
    end

    let (is_boundary) = is_le(iterator, window_size - 2)

    if is_boundary == 1:
        let (curr_window_size) = Math64x61_fromFelt(iterator + 1)
        let (window_sum) = find_sum(tail_window_len, tail_window, iterator + 1, 0)
        let (mean_window) = Math64x61_div(window_sum, curr_window_size)

        assert avg_array[iterator] = mean_window

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
        let (curr_window_size) = Math64x61_fromFelt(window_size)
        let (window_sum) = find_sum(tail_window_len, tail_window, window_size, 0)
        let (mean_window) = Math64x61_div(window_sum, curr_window_size)

        assert avg_array[iterator] = mean_window

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

    if avg_array_len == 0:
        return (iterator, upper_array, iterator, lower_array)
    end

    local mean = [avg_array]
    mean_64.write(mean)
    let (is_boundary) = is_le(iterator, window_size - 2)

    if is_boundary == 1:
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

        assert lower_array[iterator] = lower
        assert upper_array[iterator] = upper

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
        let (curr_window_size) = Math64x61_fromFelt(window_size)
        let (std_deviation) = find_std(tail_window_len, tail_window, mean, window_size, 0)

        let curr_size = curr_window_size - NUM_1

        let (std_temp) = Math64x61_div(std_deviation, curr_size)
        let (movstd) = Math64x61_sqrt(std_temp)
        let (movstd_const) = Math64x61_mul(movstd, NUM_STD)

        let (lower) = Math64x61_sub(mean, movstd_const)
        let (upper) = Math64x61_add(mean, movstd_const)

        assert lower_array[iterator] = lower
        assert upper_array[iterator] = upper

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

func calc_jump{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    mark_prices_len : felt, mark_prices : felt*, upper_array_len : felt, upper_array : felt*, lower_array_len : felt, lower_array : felt*, upper_jump_len : felt, upper_jump : felt*, lower_jump_len : felt, lower_jump : felt*, iterator : felt) -> (upper_jump_len : felt, upper_jump : felt*, lower_jump_len : felt, lower_jump : felt*):
    if mark_prices_len == 0:
        return (upper_jump_len, upper_jump, lower_jump_len, lower_jump)
    end

    let (upper_diff) = Math64x61_sub([mark_prices], [upper_array])
    let (lower_diff) = Math64x61_sub([lower_array], [mark_prices])

    let (is_upper) = is_le(upper_diff, 0)
    let (is_lower) = is_le(lower_diff, 0)

    if is_upper == 1:
        assert upper_jump[iterator] = 0
    else:
        assert upper_jump[iterator] = upper_diff
    end

    if is_lower == 1:
        assert lower_jump[iterator] = 0
    else:
        assert lower_jump[iterator] = lower_diff
    end

    return calc_jump(mark_prices_len - 1, mark_prices + 1, upper_array_len - 1, upper_array + 1, lower_array_len - 1, lower_array + 1, upper_jump_len + 1, upper_jump, lower_jump_len + 1, lower_jump, iterator + 1) 
end

@external
func calculate_abr{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    index_prices_len : felt, index_prices : felt*, mark_prices_len : felt, mark_prices : felt*
) -> (upper_array_len : felt, upper_array : felt*):
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

    # Calculate the premium
    let (diff : felt*) = alloc()
    let (diff_len : felt, diff : felt*) = calc_diff(
        index_prices_len, index_prices, mark_prices_len, mark_prices, 0, diff, 0
    )

    let (premium : felt*) = alloc()
    let (premium_len : felt, premium : felt*) = movavg(
        diff_len, diff, diff_len, diff, 3, 0, premium, 0
    )

    # Calculate ABR-jump
    let (upper_jump : felt*) = alloc()
    let (lower_jump : felt*) = alloc()


    return (premium_len, premium)
end
