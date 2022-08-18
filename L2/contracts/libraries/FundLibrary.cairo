%lang starknet

from starkware.cairo.common.bool import FALSE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address

from contracts.Constants import AdminAuth_INDEX, EmergencyFund_INDEX, ManageFunds_ACTION
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_add, Math64x61_sub

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

# Stores the mapping from market_id to its balance for ABR fund contract and
# asset_id to balance for other fund contracts
@storage_var
func balance_mapping(id : felt) -> (amount : felt):
end

# @notice function to initialize registry address and contract version
# @param resgitry_address_ Address of the AuthorizedRegistry contract
# @param contract_version_ Version of this contract
func initialize{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, contract_version_ : felt
):
    with_attr error_message("Registry address and version cannot be 0"):
        assert_not_zero(registry_address_)
        assert_not_zero(contract_version_)
    end

    registry_address.write(value=registry_address_)
    contract_version.write(value=contract_version_)
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
    let (amount) = balance_mapping.read(id=asset_id_)
    return (amount)
end

# @notice view function to get the address of Authorized registry contract
# @return address - Address of Authorized registry contract
@view
func get_registry_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    address : felt
):
    let (current_registry_address) = registry_address.read()
    return (current_registry_address)
end

# @notice view function to get current contract version
# @return contract_version - version of the contract
@view
func get_contract_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    contract_version : felt
):
    let (version) = contract_version.read()
    return (version)
end

######################
# Internal Functions #
######################

# @notice function to set balance
# @param asset_id_ - target asset_id
# @param amount_ - value to add to asset_id's balance in insurance
func set_balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    balance_mapping.write(id=asset_id_, value=amount_)
    return ()
end

# @notice add amount to asset_id's balance
# @param asset_id_ - target asset_id
# @param amount_ - value to add to asset_id's balance
func fund_contract{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
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

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    let current_amount : felt = balance_mapping.read(id=asset_id_)
    let updated_amount : felt = Math64x61_add(current_amount, amount_)

    if access == FALSE:
        let (emergency_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=EmergencyFund_INDEX, version=version
        )

        with_attr error_message("Caller is not authorized to do the transfer"):
            assert caller = emergency_address
        end

        balance_mapping.write(id=asset_id_, value=updated_amount)
    else:
        balance_mapping.write(id=asset_id_, value=updated_amount)
    end

    return ()
end

# @notice Manually deduct amount from asset_id's balance
# @param asset_id_ - target asset_id
# @param amount_ - value to deduct from asset_id's balance
func defund_contract{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
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

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    let current_amount : felt = balance_mapping.read(id=asset_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount_, current_amount)
    end
    let updated_amount : felt = Math64x61_sub(current_amount, amount_)

    if access == FALSE:
        let (emergency_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=EmergencyFund_INDEX, version=version
        )

        with_attr error_message("Caller is not authorized to do the transfer"):
            assert caller = emergency_address
        end

        balance_mapping.write(id=asset_id_, value=updated_amount)
    else:
        balance_mapping.write(id=asset_id_, value=updated_amount)
    end

    return ()
end

# @notice Deposit amount for an id by an order
# @param id_ - market_id for ABR fund contract and asset_id for other fund contracts
# @param amount_ - value to be added to asset_id's or market_id's balance
# @param index_ - ABR_PAYMENT_INDEX for ABR fund contract and Trading_INDEX for other fund contracts
func deposit_to_contract{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt, amount_ : felt, index_ : felt
):
    # Auth Check
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=index_, version=version
    )

    with_attr error_message("Caller is not authorized to perform deposit"):
        assert caller = contract_address
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    let current_amount : felt = balance_mapping.read(id=id_)
    let updated_amount : felt = Math64x61_add(current_amount, amount_)

    balance_mapping.write(id=id_, value=updated_amount)

    return ()
end

# @notice Withdraw amount for an id by an order
# @param id_ - market_id for ABR fund contract and asset_id for other fund contracts
# @param amount_ - value to deduct from asset_id's or market_id's balance
# @param index_ - ABR_PAYMENT_INDEX for ABR fund contract and Trading_INDEX for other fund contracts
func withdraw_from_contract{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt, amount_ : felt, index_ : felt
):
    # Auth Check
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=index_, version=version
    )

    with_attr error_message("Caller is not authorized to perform withdraw"):
        assert caller = contract_address
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    let current_amount : felt = balance_mapping.read(id=id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount_, current_amount)
    end
    let updated_amount : felt = Math64x61_sub(current_amount, amount_)

    balance_mapping.write(id=id_, value=updated_amount)

    return ()
end

# @notice Manually add amount to id's balance
# @param id_ - market_id for ABR fund contract and asset_id for emergency fund contract
# @param amount_ - value to add to market_id's or asset_id's balance
func fund_abr_or_emergency{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt, amount_ : felt
):
    with_attr error_message("Not authorized to manage funds"):
        let (registry) = registry_address.read()
        let (version) = contract_version.read()
        verify_caller_authority(registry, version, ManageFunds_ACTION)
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    let current_amount : felt = balance_mapping.read(id=id_)
    let updated_amount : felt = Math64x61_add(current_amount, amount_)

    balance_mapping.write(id=id_, value=updated_amount)

    return ()
end

# @notice Manually deduct amount from id's balance
# @param id_ - market_id for ABR fund contract and asset_id for emergency fund contract
# @param amount_ - value to deduct from market_id's or asset_id's balance
func defund_abr_or_emergency{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt, amount_ : felt
):
    with_attr error_message("Not authorized to manage funds"):
        let (registry) = registry_address.read()
        let (version) = contract_version.read()
        verify_caller_authority(registry, version, ManageFunds_ACTION)
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    let current_amount : felt = balance_mapping.read(id=id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount_, current_amount)
    end
    let updated_amount : felt = Math64x61_sub(current_amount, amount_)
    balance_mapping.write(id=id_, value=updated_amount)

    return ()
end
