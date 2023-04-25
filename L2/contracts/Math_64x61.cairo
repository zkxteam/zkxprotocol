%lang starknet

from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.pow import pow
from starkware.cairo.common.math import (
    abs_value,
    assert_in_range,
    sqrt,
    sign,
    signed_div_rem,
    unsigned_div_rem,
)

// ////////////
// Constants //
// ////////////

// 0x010000000000000000 or 18446744073709551616
const Math64x61_INT_PART = 2 ** 64;

// 0x002000000000000000 or 2305843009213693952
const Math64x61_FRACT_PART = 2 ** 61;

// 0x20000000000000000000000000000000 or 42535295865117307932921825928971026432
const Math64x61_BOUND = 2 ** 125;

// 0x002000000000000000 or 2305843009213693952
const Math64x61_ONE = 1 * Math64x61_FRACT_PART;
const Math64x61_ONE_NEGATIVE = -1 * Math64x61_FRACT_PART;
const Math64x61_TWO = 4611686018427387904;
const Math64x61_FOUR = 9223372036854775808;
const Math64x61_FIVE = 11529215046068469760;
const Math64x61_TEN = 10 * Math64x61_FRACT_PART;

// E (~2.7182) * ONE (2305843009213693952)
const Math64x61_E = 6267931151224907085;

// /////////////
// Assertions //
// /////////////

// Validates that X is a valid Math64x61 value
func Math64x61_assert64x61{range_check_ptr}(x: felt) {
    assert_in_range(x, -Math64x61_BOUND, Math64x61_BOUND);
    return ();
}

// Validates that X is a positive Math64x61 value. X must be >= 0.000'000'000'000'000'001
func Math64x61_assertPositive64x61{range_check_ptr}(x: felt) {
    assert_in_range(x, 1, Math64x61_BOUND);
    return ();
}

// /////////////
// Conversion //
// /////////////

// Converts a felt with decimals to a fixed point value ensuring no overflow occurs
func Math64x61_fromDecimalFelt{range_check_ptr}(x: felt, decimals: felt) -> (res: felt) {
    assert_in_range(decimals, 1, 19);
    let (ten_power_decimals) = pow(10, decimals);
    let (res) = Math64x61_div(x, ten_power_decimals);
    return (res,);
}

// Converts an integer felt value that has no decimals to a fixed point value (window_size, iterator etc.)
func Math64x61_fromIntFelt{range_check_ptr}(x: felt) -> (res: felt) {
    assert_in_range(x, -Math64x61_INT_PART, Math64x61_INT_PART);
    let res = x * Math64x61_FRACT_PART;
    return (res,);
}

// Converts a fixed point value to a felt with decimals, truncating the fractional component
func Math64x61_toDecimalFelt{range_check_ptr}(x: felt, decimals: felt) -> (res: felt) {
    let (ten_power_decimals) = pow(10, decimals);
    let (res) = Math64x61_mul(x, ten_power_decimals);
    return (res,);
}

// Converts a fixed point value to a felt, truncating the fractional component
func Math64x61_toFelt{range_check_ptr}(x: felt) -> (res: felt) {
    let (res, _) = signed_div_rem(x, Math64x61_FRACT_PART, Math64x61_BOUND);
    return (res,);
}

// //////////////////
// Math operations //
// //////////////////

// Approximates a 64.61 value to a specific number of decimal places
func Math64x61_round{range_check_ptr}(x: felt, precision: felt) -> (res: felt) {
    alloc_locals;
    local value;

    with_attr error_message("Math64x61: Error in Math64x61_round") {
        Math64x61_assert64x61(x);
        assert_in_range(precision, 0, 19);
    }

    local is_negative;
    let x_abs = abs_value(x);
    if (x_abs != x) {
        assert is_negative = TRUE;
    } else {
        assert is_negative = FALSE;
    }

    let (ten_power_precision) = pow(10, precision + 1);
    let prod = x_abs * ten_power_precision;
    let (int_val, mod_val) = unsigned_div_rem(prod, Math64x61_TEN);
    let (mod_val_floor) = Math64x61_floor(mod_val);
    let is_less = is_le(mod_val_floor, Math64x61_FOUR);
    if (is_less == TRUE) {
        value = int_val;
    } else {
        value = int_val + 1;
    }

    // Division with 10^decimals is done before converting to 64x61 to avoid overflow
    // Finding 64x61 form of integer part
    let (ten_power) = pow(10, precision);
    let (quo, mod) = unsigned_div_rem(value, ten_power);
    let (quo_64x61) = Math64x61_fromIntFelt(quo);
    // Finding 64x61 form of decimal part
    let (mod_64x61) = Math64x61_fromIntFelt(mod);
    let (ten_power_precision_64x61) = Math64x61_fromIntFelt(ten_power);
    let (decimal_part_64x61) = Math64x61_div(mod_64x61, ten_power_precision_64x61);
    // Adding both integer and decimal part
    let (res) = Math64x61_add(quo_64x61, decimal_part_64x61);

    if (is_negative == TRUE) {
        let (res_negative) = Math64x61_mul(res, Math64x61_ONE_NEGATIVE);
        return (res_negative,);
    }
    return (res,);
}

// Calculates the floor of a 64.61 value
func Math64x61_floor{range_check_ptr}(x: felt) -> (res: felt) {
    Math64x61_assert64x61(x);
    let (int_val, mod_val) = signed_div_rem(x, Math64x61_ONE, Math64x61_BOUND);
    let res = x - mod_val;
    Math64x61_assert64x61(res);
    return (res,);
}

// Calculates the ceiling of a 64.61 value
func Math64x61_ceil{range_check_ptr}(x: felt) -> (res: felt) {
    Math64x61_assert64x61(x);
    let (int_val, mod_val) = signed_div_rem(x, Math64x61_ONE, Math64x61_BOUND);
    if (mod_val != 0) {
        tempvar res = (int_val + 1) * Math64x61_ONE;
        Math64x61_assert64x61(res);
    } else {
        tempvar res = int_val * Math64x61_ONE;
        Math64x61_assert64x61(res);
    }
    return (res,);
}

// Returns the minimum of two values
func Math64x61_min{range_check_ptr}(x: felt, y: felt) -> (res: felt) {
    Math64x61_assert64x61(x);
    Math64x61_assert64x61(y);

    let x_le = is_le(x, y);

    if (x_le == 1) {
        return (x,);
    } else {
        return (y,);
    }
}

// Returns the maximum of two values
func Math64x61_max{range_check_ptr}(x: felt, y: felt) -> (res: felt) {
    Math64x61_assert64x61(x);
    Math64x61_assert64x61(y);

    let x_le = is_le(x, y);

    if (x_le == 1) {
        return (y,);
    } else {
        return (x,);
    }
}

// Convenience addition method to assert no overflow before returning
@view
func Math64x61_add{range_check_ptr}(x: felt, y: felt) -> (res: felt) {
    Math64x61_assert64x61(x);
    Math64x61_assert64x61(y);

    let res = x + y;
    Math64x61_assert64x61(res);
    return (res,);
}

// Convenience subtraction method to assert no overflow before returning
@view
func Math64x61_sub{range_check_ptr}(x: felt, y: felt) -> (res: felt) {
    Math64x61_assert64x61(x);
    Math64x61_assert64x61(y);

    let res = x - y;
    Math64x61_assert64x61(res);
    return (res,);
}

// Multiples two fixed point values and checks for overflow before returning
@view
func Math64x61_mul{range_check_ptr}(x: felt, y: felt) -> (res: felt) {
    Math64x61_assert64x61(x);
    Math64x61_assert64x61(y);

    tempvar product = x * y;
    let (res, _) = signed_div_rem(product, Math64x61_FRACT_PART, Math64x61_BOUND);
    Math64x61_assert64x61(res);
    return (res,);
}

// Divides two fixed point values and checks for overflow before returning
// Both values may be signed (i.e. also allows for division by negative b)
@view
func Math64x61_div{range_check_ptr}(x: felt, y: felt) -> (res: felt) {
    alloc_locals;
    Math64x61_assert64x61(x);
    Math64x61_assert64x61(y);

    let div = abs_value(y);
    let div_sign = sign(y);
    tempvar product = x * Math64x61_FRACT_PART;
    let (res_u, _) = signed_div_rem(product, div, Math64x61_BOUND);
    Math64x61_assert64x61(res_u);
    return (res=res_u * div_sign);
}

// Calclates the value of x^y and checks for overflow before returning
// x is a 64x61 fixed point value
// y is a standard felt (int)
func Math64x61__pow_int{range_check_ptr}(x: felt, y: felt) -> (res: felt) {
    alloc_locals;
    Math64x61_assert64x61(x);
    let exp_sign = sign(y);
    let exp_val = abs_value(y);

    if (exp_sign == 0) {
        return (Math64x61_ONE,);
    }

    if (exp_sign == -1) {
        let (num) = Math64x61__pow_int(x, exp_val);
        return Math64x61_div(Math64x61_ONE, num);
    }

    let (half_exp, rem) = unsigned_div_rem(exp_val, 2);
    let (half_pow) = Math64x61__pow_int(x, half_exp);
    let (res_p) = Math64x61_mul(half_pow, half_pow);

    if (rem == 0) {
        Math64x61_assert64x61(res_p);
        return (res_p,);
    } else {
        let (res) = Math64x61_mul(res_p, x);
        Math64x61_assert64x61(res);
        return (res,);
    }
}

// Calclates the value of x^y and checks for overflow before returning
// x is a 64x61 fixed point value
// y is a 64x61 fixed point value
func Math64x61_pow{range_check_ptr}(x: felt, y: felt) -> (res: felt) {
    alloc_locals;
    Math64x61_assert64x61(x);
    Math64x61_assert64x61(y);
    let (y_int, y_frac) = signed_div_rem(y, Math64x61_ONE, Math64x61_BOUND);

    // use the more performant integer pow when y is an int
    if (y_frac == 0) {
        return Math64x61__pow_int(x, y_int);
    }

    // x^y = exp(y*ln(x)) for x > 0 (will error for x < 0
    let (ln_x) = Math64x61_ln(x);
    let (y_ln_x) = Math64x61_mul(y, ln_x);
    let (res) = Math64x61_exp(y_ln_x);
    return (res,);
    // Math64x61_assert64x61(res)
    // return (res)
}

// Calculates the square root of a fixed point value
// x must be positive
@view
func Math64x61_sqrt{range_check_ptr}(x: felt) -> (res: felt) {
    alloc_locals;
    Math64x61_assert64x61(x);
    let root = sqrt(x);
    let scale_root = sqrt(Math64x61_FRACT_PART);
    let (res, _) = signed_div_rem(root * Math64x61_FRACT_PART, scale_root, Math64x61_BOUND);
    Math64x61_assert64x61(res);
    return (res,);
}

// Calculates the most significant bit where x is a fixed point value
// TODO: use binary search to improve performance
func Math64x61__msb{range_check_ptr}(x: felt) -> (res: felt) {
    alloc_locals;

    let cmp = is_le(x, Math64x61_FRACT_PART);

    if (cmp == 1) {
        return (0,);
    }

    let (div, _) = unsigned_div_rem(x, 2);
    let (rest) = Math64x61__msb(div);
    local res = 1 + rest;
    Math64x61_assert64x61(res);
    return (res,);
}

// Calculates the binary exponent of x: 2^x
func Math64x61_exp2{range_check_ptr}(x: felt) -> (res: felt) {
    alloc_locals;

    let exp_sign = sign(x);

    if (exp_sign == 0) {
        return (Math64x61_ONE,);
    }

    let exp_value = abs_value(x);
    let (int_part, frac_part) = unsigned_div_rem(exp_value, Math64x61_FRACT_PART);
    let (int_res) = Math64x61__pow_int(2 * Math64x61_ONE, int_part);

    // 1.069e-7 maximum error
    const a1 = 2305842762765193127;
    const a2 = 1598306039479152907;
    const a3 = 553724477747739017;
    const a4 = 128818789015678071;
    const a5 = 20620759886412153;
    const a6 = 4372943086487302;

    let (r6) = Math64x61_mul(a6, frac_part);
    let (r5) = Math64x61_mul(r6 + a5, frac_part);
    let (r4) = Math64x61_mul(r5 + a4, frac_part);
    let (r3) = Math64x61_mul(r4 + a3, frac_part);
    let (r2) = Math64x61_mul(r3 + a2, frac_part);
    tempvar frac_res = r2 + a1;

    let (res_u) = Math64x61_mul(int_res, frac_res);

    if (exp_sign == -1) {
        let (res_i) = Math64x61_div(Math64x61_ONE, res_u);
        Math64x61_assert64x61(res_i);
        return (res_i,);
    } else {
        Math64x61_assert64x61(res_u);
        return (res_u,);
    }
}

// Calculates the natural exponent of x: e^x
func Math64x61_exp{range_check_ptr}(x: felt) -> (res: felt) {
    const mod = 3326628274461080623;
    let (bin_exp) = Math64x61_mul(x, mod);
    let (res) = Math64x61_exp2(bin_exp);
    return (res,);
}

// Calculates the binary logarithm of x: log2(x)
// x must be greather than zero
func Math64x61_log2{range_check_ptr}(x: felt) -> (res: felt) {
    alloc_locals;
    Math64x61_assert64x61(x);

    if (x == Math64x61_ONE) {
        return (0,);
    }

    let is_frac = is_le(x, Math64x61_FRACT_PART - 1);

    // Compute negative inverse binary log if 0 < x < 1
    if (is_frac == 1) {
        let (div) = Math64x61_div(Math64x61_ONE, x);
        let (res_i) = Math64x61_log2(div);
        return (-res_i,);
    }

    let (x_over_two, _) = unsigned_div_rem(x, 2);
    let (b) = Math64x61__msb(x_over_two);
    let (divisor) = pow(2, b);
    let (norm, _) = unsigned_div_rem(x, divisor);

    // 4.233e-8 maximum error
    const a1 = -7898418853509069178;
    const a2 = 18803698872658890801;
    const a3 = -23074885139408336243;
    const a4 = 21412023763986120774;
    const a5 = -13866034373723777071;
    const a6 = 6084599848616517800;
    const a7 = -1725595270316167421;
    const a8 = 285568853383421422;
    const a9 = -20957604075893688;

    let (r9) = Math64x61_mul(a9, norm);
    let (r8) = Math64x61_mul(r9 + a8, norm);
    let (r7) = Math64x61_mul(r8 + a7, norm);
    let (r6) = Math64x61_mul(r7 + a6, norm);
    let (r5) = Math64x61_mul(r6 + a5, norm);
    let (r4) = Math64x61_mul(r5 + a4, norm);
    let (r3) = Math64x61_mul(r4 + a3, norm);
    let (r2) = Math64x61_mul(r3 + a2, norm);
    local norm_res = r2 + a1;

    let (int_part) = Math64x61_fromIntFelt(b);
    local res = int_part + norm_res;
    Math64x61_assert64x61(res);
    return (res,);
}

// Calculates the natural logarithm of x: ln(x)
// x must be greater than zero
@view
func Math64x61_ln{range_check_ptr}(x: felt) -> (res: felt) {
    Math64x61_assert64x61(x);
    const ln_2 = 1598288580650331957;
    let (log2_x) = Math64x61_log2(x);
    let (product) = Math64x61_mul(log2_x, ln_2);
    return (product,);
}

// Calculates the base 10 log of x: log10(x)
// x must be greater than zero
func Math64x61_log10{range_check_ptr}(x: felt) -> (res: felt) {
    Math64x61_assert64x61(x);
    const log10_2 = 694127911065419642;
    let (log10_x) = Math64x61_log2(x);
    let (product) = Math64x61_mul(log10_x, log10_2);
    return (product,);
}

// Returns 1, if x <= y (or more precisely 0 <= y - x < RANGE_CHECK_BOUND).
// Returns 1, if (x - y) <= 10^-scale
// Returns 0, otherwise
func Math64x61_is_le{range_check_ptr}(x: felt, y: felt, scale: felt) -> (res: felt) {
    alloc_locals;
    with_attr error_message("Math64x61: Error in Math64x61_is_le") {
        Math64x61_assert64x61(x);
        Math64x61_assert64x61(y);
        assert_in_range(scale, 0, 19);
    }

    let (x_round) = Math64x61_round(x, scale);
    let (y_round) = Math64x61_round(y, scale);
    let is_less = is_le(x_round, y_round);
    return (is_less,);
}

// Verifies that x <= y
func Math64x61_assert_le{range_check_ptr}(x: felt, y: felt, scale: felt) {
    let (res) = Math64x61_is_le(x, y, scale);
    assert res = TRUE;
    return ();
}

// Returns 1, if x == y
// Returns 1, if |x - y| <= 10^-scale
// Returns 0, otherwise
func Math64x61_is_equal{range_check_ptr}(x: felt, y: felt, scale: felt) -> (res: felt) {
    alloc_locals;

    with_attr error_message("Math64x61: Error in Math64x61_is_equal") {
        Math64x61_assert64x61(x);
        Math64x61_assert64x61(y);
        assert_in_range(scale, 0, 19);
    }

    let (x_round) = Math64x61_round(x, scale);
    let (y_round) = Math64x61_round(y, scale);
    if (x_round == y_round) {
        return (TRUE,);
    } else {
        return (FALSE,);
    }
}

// Verifies that x == y
func Math64x61_assert_equal{range_check_ptr}(x: felt, y: felt, scale: felt) {
    let (res) = Math64x61_is_equal(x, y, scale);
    assert res = TRUE;
    return ();
}
