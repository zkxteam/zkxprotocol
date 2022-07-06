%lang starknet

%builtins pedersen range_check ecdsa

from contracts.Constants import (
    AdminAuth_INDEX,
    Holding_INDEX,
    LiquidityFund_INDEX,
    InsuranceFund_INDEX,
    ManageFunds_ACTION
)
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.interfaces.IHolding import IHolding
from contracts.interfaces.ILiquidityFund import ILiquidityFund
from contracts.interfaces.IInsuranceFund import IInsuranceFund
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero, assert_le

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of Authorized Registry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# @notice Stores the mapping from asset_id to its balance
@storage_var
func balance_mapping(asset_id : felt) -> (amount : felt):
end

# @notice Constructor of the smart-contract
# @param registry_address_ Address of the AuthorizedRegistry contract
# @param version_ Version of this contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):
    registry_address.write(value=registry_address_)
    contract_version.write(value=version_)
    return ()
end

# @notice gets the amount of the balance for the asset_id (asset)
# @param asset_id - Target asset_id
# @returns amount - Balance of the corresponding asset
@view
func balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt
) -> (amount : felt):
    let (amount) = balance_mapping.read(asset_id=asset_id_)
    return (amount)
end

# @notice Manually add amount to asset_id's balance by admins only
# @param asset_id - target asset_id
# @param amount - value to add to asset_id's balance
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    )

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=ManageFunds_ACTION
    )
    assert_not_zero(access)

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    balance_mapping.write(asset_id=asset_id_, value=current_amount + amount)
    return ()
end

# @notice Manually deduct amount from asset_id's balance by admins only
# @param asset_id_ - target asset_id
# @param amount - value to add to asset_id's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    )

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=ManageFunds_ACTION
    )
    assert_not_zero(access)

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount, current_amount)
    end
    balance_mapping.write(asset_id=asset_id_, value=current_amount - amount)

    return ()
end

# @notice Fund holding contract by reducing funds from emergency contract
# @param asset_id_ - target asset_id
# @param amount - value to add to asset_id's balance in holding
@external
func fund_holding{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals
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
    assert_not_zero(access)

    # Get holding contract address
    let (holding_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Holding_INDEX, version=version
    )

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    balance_mapping.write(asset_id=asset_id_, value=current_amount - amount)

    IHolding.fund(contract_address=holding_address, asset_id_=asset_id_, amount=amount)

    return ()
end

# @notice Fund Liquidity contract by reducing funds from emergency contract
# @param asset_id_ - target asset_id
# @param amount - value to add to asset_id's balance in liquidity
@external
func fund_liquidity{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals
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
    assert_not_zero(access)

    # Get liquidity fund contract address
    let (liquidity_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=LiquidityFund_INDEX, version=version
    )

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    balance_mapping.write(asset_id=asset_id_, value=current_amount - amount)

    IHolding.fund(contract_address=liquidity_address, asset_id_=asset_id_, amount=amount)

    return ()
end

# @notice Fund Insurance contract by reducing funds from emergency contract
# @param asset_id_ - target asset_id
# @param amount - value to add to asset_id's balance in insurance
@external
func fund_insurance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount : felt
):
    alloc_locals
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
    assert_not_zero(access)

    # Get insurance fund contract address
    let (insurance_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=InsuranceFund_INDEX, version=version
    )

    let current_amount : felt = balance_mapping.read(asset_id=asset_id_)
    balance_mapping.write(asset_id=asset_id_, value=current_amount - amount)

    IHolding.fund(contract_address=insurance_address, asset_id_=asset_id_, amount=amount)

    return ()
end

# @notice Manually deduct amount from asset_id's balance from holding fund and transfer to emergency fund
# @param asset_id - target asset_id
# @param amount - value to add to asset_id's balance
@external
func defund_holding{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    )

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=ManageFunds_ACTION
    )
    assert_not_zero(access)

    # Get holding contract address
    let (holding_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Holding_INDEX, version=version
    )

    IHolding.defund(contract_address=holding_address, asset_id_=asset_id, amount=amount)

    let current_amount : felt = balance_mapping.read(asset_id=asset_id)
    balance_mapping.write(asset_id=asset_id, value=current_amount + amount)

    return ()
end

# @notice Manually deduct amount from asset_id's balance from insurance fund and transfer to emergency fund
# @param asset_id - target asset_id
# @param amount - value to add to asset_id's balance
@external
func defund_insurance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    )

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=ManageFunds_ACTION
    )
    assert_not_zero(access)

    # Get insurance fund contract address
    let (insurance_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=InsuranceFund_INDEX, version=version
    )

    IInsuranceFund.defund(contract_address=insurance_address, asset_id_=asset_id, amount=amount)

    let current_amount : felt = balance_mapping.read(asset_id=asset_id)
    balance_mapping.write(asset_id=asset_id, value=current_amount + amount)

    return ()
end

# @notice Manually deduct amount from asset_id's balance from liquidity fund and transfer to emergency fund
# @param asset_id - target asset_id
# @param amount - value to add to asset_id's balance
@external
func defund_liquidity{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id : felt, amount : felt
):
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    )

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=ManageFunds_ACTION
    )
    assert_not_zero(access)

    # Get liquidity contract address
    let (liquidity_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=LiquidityFund_INDEX, version=version
    )

    ILiquidityFund.defund(contract_address=liquidity_address, asset_id_=asset_id, amount=amount)

    let current_amount : felt = balance_mapping.read(asset_id=asset_id)
    balance_mapping.write(asset_id=asset_id, value=current_amount + amount)

    return ()
end