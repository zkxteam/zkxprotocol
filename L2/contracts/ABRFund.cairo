%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero, assert_nn, assert_le
from contracts.interfaces.IMarkets import IMarkets
from contracts.interfaces.IABR import IABR
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.Constants import ABR_PAYMENT_INDEX

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of Authorized Registry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# @notice Stores the mapping from market_id to its balance
@storage_var
func balance_mapping(market_id : felt) -> (amount : felt):
end

# @notice Constructor of the smart-contract
# @param resgitry_address_ Address of the AuthorizedRegistry contract
# @param version_ Version of this contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):
    registry_address.write(value=registry_address_)
    contract_version.write(value=version_)
    return ()
end

# @notice Manually add amount to market_id's balance
# @param market_id_ - target market_id
# @param amount - value to add to market_id's balance
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=0, version=version
    )

    # Auth Check
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=5
    )

    if access == 0:
        let (emergency_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=8, version=version
        )

        with_attr error_message("Caller is not authorized to do the transfer"):
            assert caller = emergency_address
        end

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    let current_amount : felt = balance_mapping.read(market_id=market_id_)
    balance_mapping.write(market_id=market_id_, value=current_amount + amount)

    return ()
end

# @notice Manually deduct amount from market_id's balance
# @param market_id_ - target market_id
# @param amount - value to deduct from market_id's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=0, version=version
    )

    # Auth Check
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=5
    )

    if access == 0:
        let (emergency_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=8, version=version
        )

        with_attr error_message("Caller is not authorized to do the transfer"):
            assert caller = emergency_address
        end

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    let current_amount : felt = balance_mapping.read(market_id=market_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount, current_amount)
    end
    balance_mapping.write(market_id=market_id_, value=current_amount - amount)

    return ()
end

# @notice Deposit amount for a market_id by an order
# @param market_id_ - target market_id
# @param amount - value to deduct from market_id's balance
# @param position_id_ - ID of the position
@external
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (abr_payment_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_PAYMENT_INDEX, version=version
    )

    with_attr error_message("Caller is not authorized to do deposit"):
        assert caller = abr_payment_address
    end

    let current_amount : felt = balance_mapping.read(market_id=market_id_)
    balance_mapping.write(market_id=market_id_, value=current_amount + amount)

    return ()
end

# @notice Withdraw amount for a market_id by an order
# @param market_id_ - target market_id
# @param amount - value to deduct from market_id's balance
# @param position_id_ - ID of the position
@external
func withdraw{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt, amount : felt
):
    alloc_locals
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (abr_payment_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_PAYMENT_INDEX, version=version
    )

    with_attr error_message("Caller is not authorized to do withdraw"):
        assert caller = abr_payment_address
    end

    let current_amount : felt = balance_mapping.read(market_id=market_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount, current_amount)
    end
    balance_mapping.write(market_id=market_id_, value=current_amount - amount)

    return ()
end

# @notice Displays the amount of the balance for the market_id(asset)
# @param market_id_ - Target market_id
# @return amount - Balance amount corresponding to the market_id
@view
func balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt
) -> (amount : felt):
    let (amount) = balance_mapping.read(market_id=market_id_)
    return (amount)
end

# @notice AuthorizedRegistry interface
@contract_interface
namespace IAuthorizedRegistry:
    func get_contract_address(index : felt, version : felt) -> (address : felt):
    end
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end
