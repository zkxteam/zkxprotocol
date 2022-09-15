%lang starknet

from starkware.cairo.common.math import assert_lt

func assert_bool(x : felt):
    assert x * (x - 1) = 0
    return ()
end

func assert_positive{range_check_ptr}(x : felt):
    assert_lt(0, x)
    return ()
end
