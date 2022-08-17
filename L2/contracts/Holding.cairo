%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin

from contracts.Constants import Trading_INDEX
from contracts.libraries.FundLibrary import (
    defund_contract,
    deposit_to_contract,
    fund_contract,
    get_balance,
    initialize,
    withdraw_from_contract,
)

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
    defund_contract(asset_id_, amount_)
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
    deposit_to_contract(asset_id_, amount_, Trading_INDEX)
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
    withdraw_from_contract(asset_id_, amount_, Trading_INDEX)
    withdraw_Holding_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end
