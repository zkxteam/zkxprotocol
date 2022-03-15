%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero

# @notice Stores the address of AdminAuth contract
@storage_var
func auth_address() -> (contract_address : felt):
end

# @notice Stores the address of Holding contract
@storage_var
func holding_address() -> (contract_address : felt):
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
    _authAddress : felt, _holdingAddress : felt
):
    auth_address.write(value=_authAddress)
    holding_address.write(value=_holdingAddress)
    return ()
end

# @notice Displays the amount of the balance for the assetID (asset)
# @param assetID - Target assetID
@view
func balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt
) -> (
    amount : felt
):
    let (amount) = balance_mapping.read(assetID = assetID_)
    return (amount)
end

# @notice Manually add amount to assetID's balance by admins only
# @param amount - value to add to assetID's balance
# @param assetID - target assetID
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=0
    )
    assert_not_zero(access)

    let current_amount : felt = balance_mapping.read(assetID = assetID_)
    balance_mapping.write(assetID = assetID_, value = current_amount + amount)
    return ()
end

# @notice Manually deduct amount from assetID's balance by admins only
# @param amount - value to add to assetID's balance
# @param assetID_ - target assetID
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, 
        address=caller, action=0
    )
    assert_not_zero(access)

    let current_amount : felt = balance_mapping.read(assetID = assetID_)
    balance_mapping.write(assetID = assetID_, value = current_amount - amount)

    return ()
end

# @notice Manually add amount to assetID's balance in emergency fund and funding contract by admins only
# @param amount - value to add to assetID's balance
# @param assetID_ - target assetID
@external
func fundHolding{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address = auth_addr, address = caller, action=0)
    assert_not_zero(access)

    let current_amount : felt = balance_mapping.read(assetID = assetID_)
    balance_mapping.write(assetID = assetID_, value = current_amount + amount)

    let (holding_addr) = holding_address.read()
    IHolding.fund(contract_address = holding_addr, assetID = assetID_, amount = amount)

    return ()
end

# @notice Manually deduct amount from assetID's balance in emergency fund and funding contract by admins only
# @param amount - value to add to assetID's balance
# @param assetID - target assetID
@external
func defundHolding{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        assetID : felt, amount : felt):
    alloc_locals

    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=0)
    assert_not_zero(access)

    let current_amount : felt = balance_mapping.read(assetID=assetID)
    balance_mapping.write(assetID=assetID, value=current_amount - amount)

    let (holding_addr) = holding_address.read()
    IHolding.defund(contract_address=holding_addr, assetID=assetID, amount=amount)

    return ()
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end

# @notice Holding interface
@contract_interface
namespace IHolding:
    func fund(assetID : felt, amount : felt):
    end

    func defund(assetID : felt, amount : felt):
    end
end
