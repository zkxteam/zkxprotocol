%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin

from contracts.libraries.FundLibrary import (
    defund_contract,
    deposit_to_contract,
    fund_contract,
    get_balance,
    get_liq_amount,
    initialize,
    withdraw_from_contract
)

##########
# Events #
##########

# Event emitted whenever fund() is called
@event
func fund_Liquidity_called(asset_id : felt, amount : felt):
end

# Event emitted whenever defund() is called
@event
func defund_Liquidity_called(asset_id : felt, amount : felt):
end

# Event emitted whenever deposit() is called
@event
func deposit_Liquidity_called(asset_id : felt, amount : felt, position_id : felt):
end

# Event emitted whenever withdraw() is called
@event
func withdraw_Liquidity_called(asset_id : felt, amount : felt, position_id : felt):
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
    initialize(registry_address_,version_)
    return ()
end

##################
# View Functions #
##################

# @notice Gets the amount of the balance for the assetID(asset)
# @param asset_id_ - Target assetID
# @return amount - Balance amount corresponding to the assetID
@view
func balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt
) -> (amount : felt):
    let (amount) = get_balance(asset_id_)
    return (amount)
end

# @notice Gets the amount owed to liquidity fund by each position
# @param asset_id_ - Target assetID
# @param position_id_ - Id of the position
# @return amount - Liquidation fee paid by the position
@view
func liq_amount{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, position_id_ : felt
) -> (amount : felt):
    let (amount) = get_liq_amount(asset_id_, position_id_)
    return (amount)
end

######################
# External Functions #
######################

# @notice Manually add amount to asset's balance
# @param asset_id_ - target asset id
# @param amount_ - value to add to asset's balance
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    fund_contract(asset_id_, amount_)
    fund_Liquidity_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Manually deduct amount from asset's balance
# @param asset_id_ - target asset id
# @param amount_ - value to deduct from asset's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt
):
    defund_contract(asset_id_, amount_)
    defund_Liquidity_called.emit(asset_id=asset_id_, amount=amount_)

    return ()
end

# @notice Deposit amount for a asset by an order
# @parama asset_id_ - target asset id
# @param amount_ - value to deduct from asset's balance
# @param position_id_ - id of the position
@external
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt, position_id_ : felt
):  
    deposit_to_contract(asset_id_, amount_, position_id_)
    deposit_Liquidity_called.emit(asset_id=asset_id_, amount=amount_, position_id=position_id_)

    return ()
end

# @notice Withdraw amount for a asset by an order
# @parama asset_id_ - target asset id
# @param amount_ - value to deduct from asset's balance
# @param position_id_ - id of the position
@external
func withdraw{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id_ : felt, amount_ : felt, position_id_ : felt
):
    withdraw_from_contract(asset_id_, amount_, position_id_)
    withdraw_Liquidity_called.emit(asset_id=asset_id_, amount=amount_, position_id=position_id_)

    return ()
end
