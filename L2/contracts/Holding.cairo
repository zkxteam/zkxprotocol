%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero, assert_nn

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

# @notice Stores the mapping from assetID to its balance
@storage_var
func balance_mapping(assetID : felt) -> (amount : felt):
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
    address: felt
):
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
    address: felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 0)
    assert_not_zero(access)
    emergency_address.write(value=address)
    return()
end

# @notice Manually add amount to assetID's balance
# @param assetID - target assetID
# @param amount - value to add to assetID's balance
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_: felt, 
    amount: felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (emergency_addr) = emergency_address.read()

    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 0)
    if access == 0:
        assert caller = emergency_addr
    end

    let current_amount : felt = balance_mapping.read(assetID = assetID_)
    balance_mapping.write(assetID = assetID_, value = current_amount + amount)

    return()
end

# @notice Manually deduct amount from assetID's balance
# @param assetID - target assetID
# @param amount - value to deduct from assetID's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_: felt, 
    amount: felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (emergency_addr) = emergency_address.read()

    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 0)
    if access == 0:
        assert caller = emergency_addr
    end

    let current_amount : felt = balance_mapping.read(assetID = assetID_)
    balance_mapping.write(assetID = assetID_, value=current_amount - amount)

    return()
end

# @notice Deposit amount for a assetID by an order
# @parama setID - target assetID
# @param amount - value to deduct from assetID's balance
@external
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_: felt, 
    amount: felt, 
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (trading_addr) = trading_address.read()

    with_attr error_message("Access is denied for deposit since caller is not trading contract in Holding contract."):
        assert caller = trading_addr
    end 
    
    let current_amount : felt = balance_mapping.read(assetID = assetID_)
    balance_mapping.write(assetID = assetID_, value = current_amount + amount)

    return()
end

# @notice Withdraw amount for a assetID by an order
# @param assetID - target assetID
# @param amount - value to deduct from assetID's balance
@external
func withdraw{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_: felt, 
    amount: felt, 
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (trading_addr) = trading_address.read()

    with_attr error_message("Access is denied for withdraw since caller is not trading contract in Holding contract."):
        assert caller = trading_addr
    end 
    
    let current_amount : felt = balance_mapping.read(assetID = assetID_)
    with_attr error_message("Updated amount shouldn't be negative in Holding contract."):
        assert_nn(current_amount - amount)
    end 
    
    balance_mapping.write(assetID = assetID_, value=current_amount - amount)

    return()
end

# @notice Displays the amount of the balance for the assetID(asset)
# @param assetID - Target assetID
# @return amount - Balance amount corresponding to the assetID
@view
func balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt
) -> (
    amount : felt
):
    let (amount) = balance_mapping.read(assetID = assetID_)
    return (amount)
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end