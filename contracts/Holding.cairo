%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero

# @notice Stores the address of AdminAuth contract
@storage_var
func auth_address() -> (contract_address : felt):
end

# @notice Stores the address of Trading contract
@storage_var
func trading_address() -> (contract_address : felt):
end

# @notice Stores the address of EmergencyFund contract
@storage_var
func emergency_address() -> (contract_address : felt):
end

# @notice Stores the mapping from ticker to its balance
@storage_var
func balance_mapping(ticker : felt) -> (amount : felt):
end

# @notice Constructor of the smart-contract
# @param _authAddress - Address of the adminAuth contract
# @param _holdingAddress - Address of the holding contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        _authAddress : felt):
    auth_address.write(value=_authAddress)
    return ()
end

# @notice Funtion to update trading contract address which
# @param address - address of trading contract
@external
func update_trading_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        address: felt):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 0)
    assert_not_zero(access)
    trading_address.write(value=address)
    return()
end

# @notice Funtion to update emergencyFund contract address which
# @param address - address of trading contract
@external
func update_emergency_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        address: felt):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 0)
    assert_not_zero(access)
    emergency_address.write(value=address)
    return()
end

# @notice Manually add amount from ticker's balance
# @param ticker - target ticker
# @param amount - value to add to ticker's balance
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ticker: felt, amount: felt):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (emergency_addr) = emergency_address.read()

    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 0)
    if access == 0:
        assert caller = emergency_addr
    end

    let current_amount : felt = balance_mapping.read(ticker=ticker)
    balance_mapping.write(ticker=ticker, value=current_amount + amount)

    return()
end

# @notice Manually deduct amount from ticker's balance
# @param ticker - target ticker
# @param amount - value to deduct from ticker's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ticker: felt, amount: felt):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (emergency_addr) = emergency_address.read()

    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 0)
    if access == 0:
        assert caller = emergency_addr
    end

    let current_amount : felt = balance_mapping.read(ticker=ticker)
    balance_mapping.write(ticker=ticker, value=current_amount - amount)

    return()
end

# @notice Deposit amount for a ticker by an order
# @param ticker - target ticker
# @param amount - value to deduct from ticker's balance
# @param order_id - Order ID associated which triggers the deposit
@external
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ticker: felt, amount: felt, order_id: felt):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (trading_addr) = trading_address.read()

    assert caller = trading_addr
    
    let current_amount : felt = balance_mapping.read(ticker=ticker)
    balance_mapping.write(ticker=ticker, value=current_amount + amount)

    return()
end

# @notice Withdraw amount for a ticker by an order
# @param ticker - target ticker
# @param amount - value to deduct from ticker's balance
# @param order_id - Order ID associated which triggers the withdrawal
@external
func withdraw{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ticker: felt, amount: felt, order_id: felt):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (trading_addr) = trading_address.read()

    assert caller = trading_addr
    
    let current_amount : felt = balance_mapping.read(ticker=ticker)
    balance_mapping.write(ticker=ticker, value=current_amount - amount)

    return()
end

# @notice Displays the amount of the balance for the ticker (asset)
# @param ticker - Target ticker
# @return amount - Balance amount corresponding to the ticker
@view
func balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(ticker : felt) -> (
        amount : felt):
    let (amount) = balance_mapping.read(ticker=ticker)
    return (amount)
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end