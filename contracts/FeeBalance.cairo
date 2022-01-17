%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_equal
from starkware.starknet.common.syscalls import get_caller_address

@storage_var
func fee_mapping(address : felt) -> (fee : felt):
end

@storage_var
func total_fee() -> (accumulated_fee : felt):
end

@external
func update_fee_mapping{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(
    address: felt,
    fee_to_add: felt
):
    let current_fee : felt = fee_mapping.read(address=address)
    let new_fee: felt = current_fee + fee_to_add
    fee_mapping.write(address=address, value=new_fee)
    let current_total_fee: felt = total_fee.read()
    let new_total_fee: felt = current_total_fee + fee_to_add
    total_fee.write(value=new_total_fee)
    return ()
end

@view
func get_total_fee{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}() -> (
    fee: felt
): 
    let (fee) = total_fee.read()
    return (fee)
end

@view
func get_user_fee{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(
    address: felt
) -> (
    fee: felt
): 
    let (fee) = fee_mapping.read(address=address)
    return (fee)
end