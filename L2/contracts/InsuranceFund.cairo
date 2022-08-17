%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le

from contracts.Constants import Trading_INDEX
from contracts.libraries.FundLibrary import (
    defund_contract,
    deposit_to_contract,
    fund_contract,
    get_balance,
    initialize,
    withdraw_from_contract,
)
from contracts.Math_64x61 import Math64x61_assert64x61

##########
# Events #
##########

# Event emitted whenever fund() is called
@event
func fund_Insurance_called(asset_id : felt, amount : felt):
end

# Event emitted whenever defund() is called
@event
func defund_Insurance_called(asset_id : felt, amount : felt):
end

# Event emitted whenever deposit() is called
@event
func deposit_Insurance_called(asset_id : felt, amount : felt, position_id : felt):
end

# Event emitted whenever withdraw() is called
@event
func withdraw_Insurance_called(asset_id : felt, amount : felt, position_id : felt):
end

###########
# Storage #
###########

# Stores the mapping from asset to positions
@storage_var
func asset_liq_position(asset_id : felt, position_id : felt) -> (value : felt):
end

###############
# Constructor #
###############

# @notice Constructor of the smart-contract
# @param resgitry_address_ Address of the AuthorizedRegistry contract
# @param version_ Version of this contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):
    initialize(registry_address_, version_)
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
    let (amount) = get_balance(asset_id_)
    return (amount)
end

# @notice Gets the amount of liquidation fees paid by each poistionID
# @param asset_id_ - Target asset_id
# @param position_id_ - Id of the position
# @return amount - Liquidation fee paid by the position
@view
func liq_amount{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, position_id_ : felt
) -> (amount : felt):
    let (amount) = asset_liq_position.read(asset_id=asset_id_, position_id=position_id_)
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
    fund_contract(asset_id_, amount_)
    fund_Insurance_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Manually deduct amount from asset_id's balance
# @param asset_id_ - target asset_id
# @param amount_ - value to deduct from asset_id's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    defund_contract(asset_id_, amount_)
    defund_Insurance_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Deposit amount for a asset_id by an order
# @param asset_id_ - target asset_id
# @param amount_ - value to deduct from asset_id's balance
# @param position_id_ - ID of the position
@external
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt, position_id_ : felt
):
    deposit_to_contract(asset_id_, amount_, Trading_INDEX)

    let current_liq_amount : felt = asset_liq_position.read(
        asset_id=asset_id_, position_id=position_id_
    )
    let updated_liq_amount : felt = current_liq_amount + amount_

    with_attr error_message("updated amount must be in 64x61 range"):
        Math64x61_assert64x61(updated_liq_amount)
    end

    asset_liq_position.write(asset_id=asset_id_, position_id=position_id_, value=updated_liq_amount)

    deposit_Insurance_called.emit(asset_id=asset_id_, amount=amount_, position_id=position_id_)

    return ()
end

# @notice Withdraw amount for a asset_id by an order
# @param asset_id_ - target asset_id
# @param amount_ - value to deduct from asset_id's balance
# @param position_id_ - ID of the position
@external
func withdraw{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt, position_id_ : felt
):
    withdraw_from_contract(asset_id_, amount_, Trading_INDEX)

    let current_liq_amount : felt = asset_liq_position.read(
        asset_id=asset_id_, position_id=position_id_
    )
    asset_liq_position.write(
        asset_id=asset_id_, position_id=position_id_, value=current_liq_amount - amount_
    )

    withdraw_Insurance_called.emit(asset_id=asset_id_, amount=amount_, position_id=position_id_)

    return ()
end
