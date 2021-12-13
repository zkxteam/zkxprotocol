%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address

@storage_var
func account_balance(address : felt) -> (balance : felt):
end

@external
func update_balance{syscall_ptr : felt*, range_check_ptr, pedersen_ptr : HashBuiltin*}(
        balance : felt):
    let (account_address) = get_caller_address()
    account_balance.write(address=account_address, value=balance)
    return ()
end

@view
func get_balance{syscall_ptr : felt*, range_check_ptr, pedersen_ptr : HashBuiltin*}(
        ) -> (balance : felt):
    let (account_address) = get_caller_address()    
    let (balance) = account_balance.read(address=account_address)
    return (balance=balance)
end
