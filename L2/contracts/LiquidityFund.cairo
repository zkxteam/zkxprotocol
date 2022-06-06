%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero, assert_nn, assert_le

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of AdminAuth contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# @notice Stores the mapping from asset_id to its balance
@storage_var
func balance_mapping(asset_id : felt) -> (amount : felt):
end

# @notice Stores the mapping from asset to positions
@storage_var
func asset_liq_position(asset_id : felt, position_id : felt) -> (value : felt):
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

# @notice Manually add amount to asset's balance
# @param asset_id_ - target asset id
# @param amount - value to add to asset's balance
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=0, version=version
    )

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=5
    )

    if access == 0:
        # Get EmergencyFund address from registry
        let (emergency_fund_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=8, version=version
        )

        with_attr error_message("Caller is not authorized to do the transfer"):
            assert caller = emergency_fund_address
        end

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    balance_mapping.write(asset_id=asset_id_, value=current_amount + amount)

    return ()
end

# @notice Manually deduct amount from asset's balance
# @param asset_id_ - target asset id
# @param amount - value to deduct from asset's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=0, version=version
    )

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=5
    )

    if access == 0:
        # Get EmergencyFund address from registry
        let (emergency_fund_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=8, version=version
        )

        with_attr error_message("Caller is not authorized to do the transfer"):
            assert caller = emergency_fund_address
        end

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
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

# @notice Deposit amount for a asset by an order
# @parama asset_id_ - target asset id
# @param amount - value to deduct from asset's balance
# @param position_id_ - id of the position
@external
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt, position_id_ : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get trading contract address
    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=5, version=version
    )

    with_attr error_message("Caller is not authorized to do the transfer"):
        assert caller = trading_address
    end

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    balance_mapping.write(asset_id=asset_id_, value=current_amount + amount)

    let current_liq_amount : felt = asset_liq_position.read(
        asset_id=asset_id_, position_id=position_id_
    )
    asset_liq_position.write(
        asset_id=asset_id_, position_id=position_id_, value=current_liq_amount + amount
    )

    return ()
end

# @notice Withdraw amount for a asset by an order
# @parama asset_id_ - target asset id
# @param amount - value to deduct from asset's balance
# @param position_id_ - id of the position
@external
func withdraw{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt, position_id_ : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get trading contract address
    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=5, version=version
    )

    with_attr error_message("Caller is not authorized to do the transfer"):
        assert caller = trading_address
    end

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount, current_amount)
    end
    balance_mapping.write(asset_id=asset_id_, value=current_amount - amount)

    let current_liq_amount : felt = asset_liq_position.read(
        asset_id=asset_id_, position_id=position_id_
    )

    asset_liq_position.write(
        asset_id=asset_id_, position_id=position_id_, value=current_liq_amount - amount
    )

    return ()
end

# @notice Displays the amount of the balance for the assetID(asset)
# @param asset_id_ - Target assetID
# @return amount - Balance amount corresponding to the assetID
@view
func balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt
) -> (amount : felt):
    let (amount) = balance_mapping.read(asset_id=asset_id_)
    return (amount)
end

# @notice Displays the amount of liquidation fees paid by each poistionID
# @param asset_id_ - Target assetID
# @param position_id_ - Id of the position
# @return amount - Liquidation fee paid by the position
@view
func liq_amount{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, position_id_ : felt
) -> (amount : felt):
    let (amount) = asset_liq_position.read(asset_id=asset_id_, position_id=position_id_)
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
