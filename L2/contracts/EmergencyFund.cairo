%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address

from contracts.Constants import (
    Holding_INDEX,
    InsuranceFund_INDEX,
    LiquidityFund_INDEX,
    ManageFunds_ACTION,
)
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IHolding import IHolding
from contracts.interfaces.IInsuranceFund import IInsuranceFund
from contracts.interfaces.ILiquidityFund import ILiquidityFund
from contracts.libraries.FundLibrary import (
    defund_abr_or_emergency,
    fund_abr_or_emergency,
    get_contract_version,
    get_registry_address,
    balance,
    initialize,
    set_balance
)
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_add, Math64x61_sub

##########
# Events #
##########

# Event emitted whenever fund() is called
@event
func fund_Emergency_called(asset_id : felt, amount : felt):
end

# Event emitted whenever defund() is called
@event
func defund_Emergency_called(asset_id : felt, amount : felt):
end

# Event emitted whenever fund_holding() is called
@event
func fund_Holding_from_Emergency_called(asset_id : felt, amount : felt):
end

# Event emitted whenever fund_liquidity() is called
@event
func fund_Liquidity_from_Emergency_called(asset_id : felt, amount : felt):
end

# Event emitted whenever fund_insurance() is called
@event
func fund_Insurance_from_Emergency_called(asset_id : felt, amount : felt):
end

# Event emitted whenever defund_holding() is called
@event
func defund_Holding_from_Emergency_called(asset_id : felt, amount : felt):
end

# Event emitted whenever defund_liquidity() is called
@event
func defund_Liquidity_from_Emergency_called(asset_id : felt, amount : felt):
end

# Event emitted whenever defund_insurance() is called
@event
func defund_Insurance_from_Emergency_called(asset_id : felt, amount : felt):
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
    initialize(registry_address_, version_)
    return ()
end

######################
# External Functions #
######################

# @notice Manually add amount to asset_id's balance by admins only
# @param asset_id - target asset_id
# @param amount_ - value to add to asset_id's balance
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    fund_abr_or_emergency(asset_id_, amount_)
    fund_Emergency_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Manually deduct amount from asset_id's balance by admins only
# @param asset_id_ - target asset_id
# @param amount_ - value to add to asset_id's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    defund_abr_or_emergency(asset_id_, amount_)
    defund_Emergency_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Fund holding contract by reducing funds from emergency contract
# @param asset_id_ - target asset_id
# @param amount_ - value to add to asset_id's balance in holding
@external
func fund_holding{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    let (registry) = get_registry_address()
    let (version) = get_contract_version()

    with_attr error_message("Caller is not authorized to manage funds"):
        verify_caller_authority(registry, version, ManageFunds_ACTION)
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    # Get holding contract address
    let (holding_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Holding_INDEX, version=version
    )
    
    let current_amount : felt = balance(asset_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount_, current_amount)
    end
    let updated_amount : felt = Math64x61_sub(current_amount, amount_)
    set_balance(asset_id_, updated_amount)

    IHolding.fund(contract_address=holding_address, asset_id_=asset_id_, amount=amount_)

    fund_Holding_from_Emergency_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Fund Liquidity contract by reducing funds from emergency contract
# @param asset_id_ - target asset_id
# @param amount_ - value to add to asset_id's balance in liquidity
@external
func fund_liquidity{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    # Verify auth
    let (registry) = get_registry_address()
    let (version) = get_contract_version()

    with_attr error_message("Caller is not authorized to manage funds"):
        verify_caller_authority(registry, version, ManageFunds_ACTION)
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    # Get liquidity fund contract address
    let (liquidity_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=LiquidityFund_INDEX, version=version
    )

    let current_amount : felt = balance(asset_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount_, current_amount)
    end
    let updated_amount : felt = Math64x61_sub(current_amount, amount_)
    set_balance(asset_id_, updated_amount)

    ILiquidityFund.fund(contract_address=liquidity_address, asset_id_=asset_id_, amount=amount_)

    fund_Liquidity_from_Emergency_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Fund Insurance contract by reducing funds from emergency contract
# @param asset_id_ - target asset_id
# @param amount_ - value to add to asset_id's balance in insurance
@external
func fund_insurance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    # Verify auth
    let (registry) = get_registry_address()
    let (version) = get_contract_version()

    with_attr error_message("Caller is not authorized to manage funds"):
        verify_caller_authority(registry, version, ManageFunds_ACTION)
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    # Get insurance fund contract address
    let (insurance_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=InsuranceFund_INDEX, version=version
    )

    let current_amount : felt = balance(asset_id_)
    with_attr error_message("Amount to be deducted is more than asset's balance"):
        assert_le(amount_, current_amount)
    end
    let updated_amount : felt = Math64x61_sub(current_amount, amount_)
    set_balance(asset_id_, updated_amount)

    IInsuranceFund.fund(contract_address=insurance_address, asset_id_=asset_id_, amount=amount_)

    fund_Insurance_from_Emergency_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Manually deduct amount from asset_id's balance from holding fund and transfer to emergency fund
# @param asset_id - target asset_id
# @param amount_ - value to add to asset_id's balance
@external
func defund_holding{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    # Verify auth
    let (registry) = get_registry_address()
    let (version) = get_contract_version()

    with_attr error_message("Caller is not authorized to manage funds"):
        verify_caller_authority(registry, version, ManageFunds_ACTION)
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    # Get holding contract address
    let (holding_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Holding_INDEX, version=version
    )
    IHolding.defund(contract_address=holding_address, asset_id_=asset_id_, amount=amount_)

    let current_amount : felt = balance(asset_id_)
    let updated_amount : felt = Math64x61_add(current_amount, amount_)
    set_balance(asset_id_, updated_amount)

    defund_Holding_from_Emergency_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Manually deduct amount from asset_id's balance from liquidity fund and transfer to emergency fund
# @param asset_id - target asset_id
# @param amount_ - value to add to asset_id's balance
@external
func defund_liquidity{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    # Verify auth
    let (registry) = get_registry_address()
    let (version) = get_contract_version()

    with_attr error_message("Caller is not authorized to manage funds"):
        verify_caller_authority(registry, version, ManageFunds_ACTION)
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    # Get liquidity contract address
    let (liquidity_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=LiquidityFund_INDEX, version=version
    )
    ILiquidityFund.defund(contract_address=liquidity_address, asset_id_=asset_id_, amount=amount_)

    let current_amount : felt = balance(asset_id_)
    let updated_amount : felt = Math64x61_add(current_amount, amount_)
    set_balance(asset_id_, updated_amount)

    defund_Liquidity_from_Emergency_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Manually deduct amount from asset_id's balance from insurance fund and transfer to emergency fund
# @param asset_id - target asset_id
# @param amount_ - value to add to asset_id's balance
@external
func defund_insurance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    # Verify auth
    let (registry) = get_registry_address()
    let (version) = get_contract_version()

    with_attr error_message("Caller is not authorized to manage funds"):
        verify_caller_authority(registry, version, ManageFunds_ACTION)
    end

    with_attr error_message("Amount cannot be 0 or negative"):
        assert_lt(0, amount_)
    end

    # Get insurance fund contract address
    let (insurance_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=InsuranceFund_INDEX, version=version
    )
    IInsuranceFund.defund(contract_address=insurance_address, asset_id_=asset_id_, amount=amount_)

    let current_amount : felt = balance(asset_id_)
    let updated_amount : felt = Math64x61_add(current_amount, amount_)
    set_balance(asset_id_, updated_amount)

    defund_Insurance_from_Emergency_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end
