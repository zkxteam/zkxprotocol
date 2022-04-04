%lang starknet
%builtins pedersen range_check ecdsa

from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.messages import send_message_to_l1
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address

@event
func increase_balance_called(
        action : felt):
end

@external
func test{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}():
    increase_balance_called.emit(action=1)
    with_attr error_message("values are not equal"):
        assert 1 = 1
    end
    return ()
end


# func inverse(x) -> (res):
#     with_attr error_message("x must not be zero. Got x={x}."):
#         return (res=1 / x)
#     end
# end

# @external
# func assert_not_equal(a, b):
#     let diff = a - b
#     with_attr error_message("a and b must be distinct."):
#         inverse(diff)
#     end
#     return ()
# end