%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_block_timestamp

from contracts.Constants import ABR_PAYMENT_INDEX
from contracts.libraries.FundLibrary import (
    defund_abr_or_emergency,
    deposit_to_contract,
    fund_abr_or_emergency,
    balance,
    initialize,
    withdraw_from_contract,
)

##########
# Events #
##########

# Event emitted whenever fund() is called
@event
func fund_ABR_called(market_id : felt, amount : felt):
end

# Event emitted whenever defund() is called
@event
func defund_ABR_called(market_id : felt, amount : felt):
end

# Event emitted whenever deposit() is called
@event
func deposit_ABR_called(
    order_id : felt, account_address : felt, market_id : felt, amount : felt, timestamp : felt
):
end

# Event emitted whenever withdraw() is called
@event
func withdraw_ABR_called(
    order_id : felt, account_address : felt, market_id : felt, amount : felt, timestamp : felt
):
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

######################
# External Functions #
######################

# @notice Manually add amount to market_id's balance
# @param market_id_ - target market_id
# @param amount_ - value to add to market_id's balance
@external
func fund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt, amount_ : felt
):
    fund_abr_or_emergency(market_id_, amount_)
    fund_ABR_called.emit(market_id=market_id_, amount=amount_)

    return ()
end

# @notice Manually deduct amount from market_id's balance
# @param market_id_ - target market_id
# @param amount_ - value to deduct from market_id's balance
@external
func defund{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt, amount_ : felt
):
    defund_abr_or_emergency(market_id_, amount_)
    defund_ABR_called.emit(market_id=market_id_, amount=amount_)

    return ()
end

# @notice Deposit amount for a market_id by an order
# @param order_id_ - ID of the position
# @param market_id_ - target market_id
# @param amount_ - value to deduct from market_id's balance
@external
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    order_id_ : felt, account_address_ : felt, market_id_ : felt, amount_ : felt
):
    deposit_to_contract(market_id_, amount_, ABR_PAYMENT_INDEX)

    # Get the latest block
    let (block_timestamp) = get_block_timestamp()
    deposit_ABR_called.emit(
        order_id=order_id_,
        account_address=account_address_,
        market_id=market_id_,
        amount=amount_,
        timestamp=block_timestamp,
    )

    return ()
end

# @notice Withdraw amount for a market_id by an order
# @param order_id_ - ID of the position
# @param market_id_ - target market_id
# @param amount_ - value to deduct from market_id's balance
@external
func withdraw{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    order_id_ : felt, account_address_ : felt, market_id_ : felt, amount_ : felt
):
    withdraw_from_contract(market_id_, amount_, ABR_PAYMENT_INDEX)

    # Get the latest block
    let (block_timestamp) = get_block_timestamp()
    withdraw_ABR_called.emit(
        order_id=order_id_,
        account_address=account_address_,
        market_id=market_id_,
        amount=amount_,
        timestamp=block_timestamp,
    )

    return ()
end
