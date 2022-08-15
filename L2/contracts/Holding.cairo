%lang starknet

from starkware.cairo.common.bool import FALSE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address

from contracts.Constants import (
    AdminAuth_INDEX,
    EmergencyFund_INDEX,
    ManageFunds_ACTION,
    Trading_INDEX,
)
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.Math_64x61 import Math64x61_assert64x61

##########
# Events #
##########

# Event emitted whenever fund() is called
@event
func fund_Holding_called(asset_id : felt, amount : felt):
end

# Event emitted whenever defund() is called
@event
func defund_Holding_called(asset_id : felt, amount : felt):
end

# Event emitted whenever deposit() is called
@event
func deposit_Holding_called(asset_id : felt, amount : felt):
end

# Event emitted whenever withdraw() is called
@event
func withdraw_Holding_called(asset_id : felt, amount : felt):
end

###########
# Storage #
###########

# Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# Stores the address of Authorized Registry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# Stores the mapping from asset_id to its balance
@storage_var
func balance_mapping(asset_id : felt) -> (amount : felt):
end

###############
# Constructor #
###############

# @notice Constructor of the smart-contract
# @param registry_address_ Address of the AuthorizedRegistry contract
# @param version_ Version of this contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):
    with_attr error_message("Registry address and version cannot be 0"):
        assert_not_zero(registry_address_)
        assert_not_zero(version_)
    end

    registry_address.write(value=registry_address_)
    contract_version.write(value=version_)
    return ()
end

##################
# View Functions #
##################

# @notice Gets the amount of the balance for the asset_id(asset)
# @param asset_id_ - Target asset_id
# @return amount - Balance amount corresponding to the asset_id
@view
func balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt
) -> (amount : felt):
    let (amount) = balance_mapping.read(asset_id=asset_id_)
    return (amount)
end

######################
# External Functions #
######################

# @notice Manually add amount to asset_id's balance
# @param asset_id_ - target asset_id
# @param amount_ - value to add to asset_id's balance
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    with_attr error_message("Amount should be in 64x61 representation"):
        Math64x61_assert64x61(amount_)
    end

    # Auth Check
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    )

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=ManageFunds_ACTION
    )
    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    let updated_amount : felt = current_amount + amount_

    with_attr error_message("updated amount must be in 64x61 range"):
        Math64x61_assert64x61(updated_amount)
    end

    if access == FALSE:
        # Get EmergencyFund address from registry
        let (emergency_fund_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=EmergencyFund_INDEX, version=version
        )

        with_attr error_message("Caller is not authorized to do the transfer"):
            assert caller = emergency_fund_address
        end

        balance_mapping.write(asset_id=asset_id_, value=updated_amount)
    else:
        balance_mapping.write(asset_id=asset_id_, value=updated_amount)
    end

    fund_Holding_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Manually deduct amount from asset_id's balance
# @param asset_id_ - target asset_id
# @param amount_ - value to deduct from asset_id's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    with_attr error_message("Amount should be in 64x61 representation"):
        Math64x61_assert64x61(amount_)
    end

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount_, current_amount)
    end

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    )

    # Auth Check
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=ManageFunds_ACTION
    )

    if access == FALSE:
        # Get EmergencyFund address from registry
        let (emergency_fund_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=EmergencyFund_INDEX, version=version
        )

        with_attr error_message("Caller is not authorized to do the transfer"):
            assert caller = emergency_fund_address
        end

        balance_mapping.write(asset_id=asset_id_, value=current_amount - amount_)
    else:
        balance_mapping.write(asset_id=asset_id_, value=current_amount - amount_)
    end

    defund_Holding_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Deposit amount for a asset_id by an order
# @parama asset_id_ - target asset_id
# @param amount_ - value to deduct from asset_id's balance
@external
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get trading contract address
    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    )

    with_attr error_message("Caller is not authorized to do the transfer"):
        assert caller = trading_address
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    with_attr error_message("Amount should be in 64x61 representation"):
        Math64x61_assert64x61(amount_)
    end

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    let updated_amount : felt = current_amount + amount_

    with_attr error_message("updated amount must be in 64x61 range"):
        Math64x61_assert64x61(updated_amount)
    end
    balance_mapping.write(asset_id=asset_id_, value=updated_amount)

    deposit_Holding_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Withdraw amount for a asset_id by an order
# @param asset_id_ - target asset_id
# @param amount_ - value to deduct from asset_id's balance
@external
func withdraw{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get trading contract address
    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    )

    with_attr error_message("Caller is not authorized to do the transfer"):
        assert caller = trading_address
    end

    with_attr error_message("Amount should be in 64x61 representation"):
        Math64x61_assert64x61(amount_)
    end

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount_, current_amount)
    end
    balance_mapping.write(asset_id=asset_id_, value=current_amount - amount_)

    withdraw_Holding_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end
