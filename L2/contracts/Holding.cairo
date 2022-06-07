%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero, assert_le

# @notice Stores the address of AdminAuth contract
@storage_var
func admin_authorized_address() -> (contract_address : felt):
end

# @notice Stores the address of Trading contract
@storage_var
func trading_address() -> (contract_address : felt):
end

# @notice Stores the address of EmergencyFund contract
@storage_var
func emergency_address() -> (contract_address : felt):
end

# @notice Stores the mapping from asset_id to its balance
@storage_var
func balance_mapping(asset_id : felt) -> (amount : felt):
end

# @notice Stores the address of the auth registry
@storage_var
func authorized_registry() -> (res : felt):
end

# @notice Constructor of the smart-contract
# @param admin_authorized_address_ - Address of the adminAuth contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    admin_authorized_address_ : felt, authorized_registry_ : felt
):
    admin_authorized_address.write(value=admin_authorized_address_)
    authorized_registry.write(value=authorized_registry_)
    return ()
end

# @notice Manually add amount to asset_id's balance
# @param asset_id - target asset_id
# @param amount - value to add to asset_id's balance
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = admin_authorized_address.read()

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=0
    )
    tempvar syscall_ptr = syscall_ptr
    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
    tempvar range_check_ptr = range_check_ptr

    if access == 0:
        let (authorized_registry_) = authorized_registry.read()
        let (is_emergency_contract) = IAuthorizedRegistry.get_registry_value(
            contract_address=authorized_registry_, address=caller, action=8
        )

        with_attr error_message("Caller is not authorized to do the transfer"):
            assert is_emergency_contract = 1
        end

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    balance_mapping.write(asset_id=asset_id_, value=current_amount + amount)

    return ()
end

# @notice Manually deduct amount from asset_id's balance
# @param asset_id - target asset_id
# @param amount - value to deduct from asset_id's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (auth_addr) = admin_authorized_address.read()

    # Auth Check
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=0
    )

    tempvar syscall_ptr = syscall_ptr
    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
    tempvar range_check_ptr = range_check_ptr

    if access == 0:
        let (authorized_registry_) = authorized_registry.read()
        let (is_emergency_contract) = IAuthorizedRegistry.get_registry_value(
            contract_address=authorized_registry_, address=caller, action=8
        )

        with_attr error_message("Caller is not authorized to do the transfer"):
            assert is_emergency_contract = 1
        end

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount, current_amount)
    end
    balance_mapping.write(asset_id=asset_id_, value=current_amount - amount)

    return ()
end

# @notice Deposit amount for a asset_id by an order
# @parama setID - target asset_id
# @param amount - value to deduct from asset_id's balance
@external
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (authorized_registry_) = authorized_registry.read()

    # Auth Check
    let (is_trading_contract) = IAuthorizedRegistry.get_registry_value(
        contract_address=authorized_registry_, address=caller, action=3
    )

    with_attr error_message("Caller is not authorized to do the transfer"):
        assert is_trading_contract = 1
    end

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    balance_mapping.write(asset_id=asset_id_, value=current_amount + amount)

    return ()
end

# @notice Withdraw amount for a asset_id by an order
# @param asset_id - target asset_id
# @param amount - value to deduct from asset_id's balance
@external
func withdraw{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (authorized_registry_) = authorized_registry.read()

    # Auth Check
    let (is_trading_contract) = IAuthorizedRegistry.get_registry_value(
        contract_address=authorized_registry_, address=caller, action=3
    )

    with_attr error_message("Caller is not authorized to do the transfer"):
        assert is_trading_contract = 1
    end

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount, current_amount)
    end
    balance_mapping.write(asset_id=asset_id_, value=current_amount - amount)

    return ()
end

# @notice Displays the amount of the balance for the asset_id(asset)
# @param asset_id - Target asset_id
# @return amount - Balance amount corresponding to the asset_id
@view
func balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt
) -> (amount : felt):
    let (amount) = balance_mapping.read(asset_id=asset_id_)
    return (amount)
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end

# @notice AuthorizedRegistry interface
@contract_interface
namespace IAuthorizedRegistry:
    func get_registry_value(address : felt, action : felt) -> (allowed : felt):
    end
end
