%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.hash_state import (
    hash_finalize,
    hash_init,
    hash_update,
    hash_update_single,
)
from starkware.cairo.common.math import (
    abs_value,
    assert_le,
    assert_nn,
    assert_not_equal,
    assert_not_zero,
)
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.pow import pow
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.starknet.common.messages import send_message_to_l1
from starkware.starknet.common.syscalls import (
    call_contract,
    get_block_timestamp,
    get_caller_address,
    get_contract_address,
    get_tx_signature,
)

from contracts.Constants import (
    ABR_PAYMENT_INDEX,
    Asset_INDEX,
    DELEVERAGING_ORDER,
    L1_ZKX_Address_INDEX,
    Liquidate_INDEX,
    LIQUIDATION_ORDER,
    LONG,
    POSITION_OPENED,
    POSITION_TO_BE_DELEVERAGED,
    POSITION_TO_BE_LIQUIDATED,
    SHORT,
    Trading_INDEX,
    WithdrawalFeeBalance_INDEX,
    WithdrawalRequest_INDEX,
)
from contracts.DataTypes import (
    Asset,
    CollateralBalance,
    LiquidatablePosition,
    Message,
    NetPositions,
    OrderRequest,
    PositionDetails,
    PositionDetailsWithMarket,
    Signature,
    WithdrawalHistory,
    WithdrawalRequestForHashing,
)

from contracts.interfaces.IAccountManager import IAccountManager
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IWithdrawalFeeBalance import IWithdrawalFeeBalance
from contracts.interfaces.IWithdrawalRequest import IWithdrawalRequest
from contracts.Math_64x61 import (
    Math64x61_add,
    Math64x61_div,
    Math64x61_fromFelt,
    Math64x61_mul,
    Math64x61_sub,
    Math64x61_toFelt,
)

##########
# Events #
##########

# Event emitted whenever collateral is transferred from account by trading
@event
func transferred_from(asset_id : felt, amount : felt):
end

# Event emitted whenever collateral is transferred to account by trading
@event
func transferred(asset_id : felt, amount : felt):
end

# Event emitted whenever collateral is transferred to account by abr payment
@event
func transferred_abr(market_id : felt, amount : felt, timestamp : felt):
end

# Event emitted whenever collateral is transferred from account by abr payment
@event
func transferred_from_abr(market_id : felt, amount : felt, timestamp : felt):
end

# Event emitted whenver a new withdrawal request is made
@event
func withdrawal_request(collateral_id : felt, amount : felt, node_operator_l2 : felt):
end

# Event emitted whenever a position is marked to be liquidated/deleveraged
@event
func liquidate_deleverage(market_id : felt, direction : felt, amount_to_be_sold : felt):
end

# Event emitted whenever asset deposited in into account
@event
func deposited(asset_id : felt, amount : felt):
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

# Stores public key associated with an account
@storage_var
func public_key() -> (res : felt):
end

# Stores balance of an asset
@storage_var
func balance(assetID : felt) -> (res : felt):
end

# Mapping of marketID, direction to PositionDetails struct
@storage_var
func position_mapping(marketID : felt, direction : felt) -> (res : PositionDetails):
end

# Mapping of orderID to portionExecuted of that order
@storage_var
func portion_executed(orderID : felt) -> (res : felt):
end

# Mapping of orderID to the timestamp of last updated value
@storage_var
func last_updated(market_id) -> (value : felt):
end

# Stores L1 address associated with the account
@storage_var
func L1_address() -> (res : felt):
end

# Stores all markets the user has position in
@storage_var
func index_to_market_array(index : felt) -> (market_id : felt):
end

# Stores the mapping from the market_id to index
@storage_var
func market_to_index_mapping(market_id : felt) -> (market_id : felt):
end

# Stores if a market exists
@storage_var
func market_is_exist(market_id) -> (res : felt):
end

# Stores all collaterals held by the user
@storage_var
func collateral_array(index : felt) -> (collateral_id : felt):
end

# Stores the length of the index_to_market_array
@storage_var
func index_to_market_array_len() -> (len : felt):
end

# Stores length of the collateral array
@storage_var
func collateral_array_len() -> (len : felt):
end

# Stores amount_to_be_sold in a position for delveraging
@storage_var
func amount_to_be_sold(order_id : felt) -> (amount : felt):
end

# Stores the position which is to be deleveraged or liquidated
@storage_var
func deleveragable_or_liquidatable_position() -> (position : LiquidatablePosition):
end

# Stores all withdrawals made by the user
@storage_var
func withdrawal_history_array(index : felt) -> (res : WithdrawalHistory):
end

# Stores length of the withdrawal history array
@storage_var
func withdrawal_history_array_len() -> (len : felt):
end

###############
# Constructor #
###############

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    public_key_ : felt, L1_address_ : felt, registry_address_ : felt, version_ : felt
):
    with_attr error_message("Registry address and version cannot be 0"):
        assert_not_zero(version_)
    end

    public_key.write(public_key_)
    L1_address.write(L1_address_)
    registry_address.write(value=registry_address_)
    contract_version.write(value=version_)
    return ()
end

##################
# View Functions #
##################

# @notice view function to get public key
# @return res - public key of an account
@view
func get_public_key{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (res) = public_key.read()
    return (res=res)
end

# @notice view function to check if the transaction signature is valid
# @param hash - Hash of the transaction parameters
# @param singature_len - Length of the signatures
# @param signature - Array of signatures
@view
func is_valid_signature{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(hash : felt, signature_len : felt, signature : felt*) -> ():
    let (_public_key) = public_key.read()

    # This interface expects a signature pointer and length to make
    # no assumption about signature validation schemes.
    # But this implementation does, and it expects a (sig_r, sig_s) pair.
    let sig_r = signature[0]
    let sig_s = signature[1]

    verify_ecdsa_signature(
        message=hash, public_key=_public_key, signature_r=sig_r, signature_s=sig_s
    )

    return ()
end

# @notice view function which checks the signature passed is valid
# @param hash - Hash of the order to check against
# @param signature - Signature passed to the contract to check against
# @param liquidator_address_ - Address of the liquidator
# @return reverts, if there is an error
@view
func is_valid_signature_order{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(hash : felt, signature : Signature, liquidator_address_ : felt) -> ():
    alloc_locals

    let sig_r = signature.r_value
    let sig_s = signature.s_value
    local pub_key

    if liquidator_address_ != 0:
        # To-Do Verify whether call came from node operator

        let (_public_key) = IAccountManager.get_public_key(contract_address=liquidator_address_)
        pub_key = _public_key

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
        tempvar ecdsa_ptr : SignatureBuiltin* = ecdsa_ptr
    else:
        let (acc_pub_key) = public_key.read()
        pub_key = acc_pub_key

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
        tempvar ecdsa_ptr : SignatureBuiltin* = ecdsa_ptr
    end

    verify_ecdsa_signature(message=hash, public_key=pub_key, signature_r=sig_r, signature_s=sig_s)
    return ()
end

# @notice view function to get the balance of an asset
# @param assetID_ - ID of an asset
# @return res - balance of an asset
@view
func get_balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt
) -> (res : felt):
    let (res) = balance.read(assetID=assetID_)
    return (res=res)
end

# @notice view function to get order details
# @param orderID_ - ID of an order
# @return res - Order details corresponding to an order
@view
func get_position_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt, direction_ : felt
) -> (res : PositionDetails):
    let (res) = position_mapping.read(marketID=market_id_, direction=direction_)
    return (res=res)
end

# @notice view function to get L1 address of the user
# @return res - L1 address of the user
@view
func get_L1_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (res) = L1_address.read()
    return (res=res)
end

# @notice view function to get deleveraged or liquidatable position
# @return order_id - Id of an order, amount_to_be_sold - amount to be sold in a position
@view
func get_deleveragable_or_liquidatable_position{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr
}() -> (market_id : felt, direction : felt, amount_to_be_sold : felt):
    let (position : LiquidatablePosition) = deleveragable_or_liquidatable_position.read()

    return (position.market_id, position.direction, position.amount_to_be_sold)
end

# @notice view function to get all use collaterals
# @return array_list_len - Length of the array_list
# @return array_list - Fully populated list of CollateralBalance
@view
func return_array_collaterals{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (array_list_len : felt, array_list : CollateralBalance*):
    let (array_list : CollateralBalance*) = alloc()
    let (array_len : felt) = collateral_array_len.read()
    return populate_array_collaterals(0, array_list, array_len)
end

# @notice view function to get withdrawal history
# @return withdrawal_list_len - Length of the withdrawal list
# @return withdrawal_list - Fully populated list of withdrawals
@view
func get_withdrawal_history{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (withdrawal_list_len : felt, withdrawal_list : WithdrawalHistory*):
    let (withdrawal_list : WithdrawalHistory*) = alloc()
    return populate_withdrawals_array(0, withdrawal_list)
end

# @notice view function to check if eight hours is complete or not
# @param market_id_ - ID of a market
# @return res - true if it is complete, else false
@view
func timestamp_check{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt
) -> (is_eight_hours : felt):
    alloc_locals
    # Get the latest block
    let (block_timestamp) = get_block_timestamp()

    # Fetch the last updated time
    let (last_call) = last_updated.read(market_id=market_id_)

    # Minimum time before the second call
    let min_time = last_call + 28800
    let (is_eight_hours) = is_le(block_timestamp, min_time)

    return (is_eight_hours)
end

##############
# L1 Handler #
##############

# @notice Function to handle deposit from L1ZKX contract
# @param from_address - The address from where deposit function is called from
# @param user - User's Metamask account address
# @param amount - The Amount of funds that user wants to withdraw
# @param assetID_ - Asset ID of the collateral that needs to be deposited
@l1_handler
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    from_address : felt, user : felt, amount : felt, assetID_ : felt
):
    alloc_locals
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get L1 ZKX contract address
    let (L1_ZKX_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=L1_ZKX_Address_INDEX, version=version
    )

    # Make sure the message was sent by the intended L1 contract
    with_attr error_message("Message must be sent by approved ZKX address"):
        assert from_address = L1_ZKX_contract_address
    end

    let (stored_L1_address) = L1_address.read()

    with_attr error_message("Only the user can initiate deposits"):
        assert stored_L1_address = user
    end

    # Get asset contract address
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    )
    # Reading token decimal field of an asset
    let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=assetID_)
    tempvar decimal = asset.token_decimal

    let (ten_power_decimal) = pow(10, decimal)
    let (decimal_in_64x61_format) = Math64x61_fromFelt(ten_power_decimal)

    let (amount_in_64x61_format) = Math64x61_fromFelt(amount)
    let (amount_in_decimal_representation) = Math64x61_div(
        amount_in_64x61_format, decimal_in_64x61_format
    )

    let (array_len) = collateral_array_len.read()
    # Read the current balance.
    let (balance_collateral) = balance.read(assetID=assetID_)

    if balance_collateral == 0:
        add_collateral(new_asset_id=assetID_, iterator=0, length=array_len)
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    # Compute and update the new balance.
    tempvar new_balance = balance_collateral + amount_in_decimal_representation
    balance.write(assetID=assetID_, value=new_balance)

    deposited.emit(asset_id=assetID_, amount=amount_in_decimal_representation)
    return ()
end

######################
# External Functions #
######################

# @notice External function called by the Trading Contract
# @param assetID_ - asset ID of the collateral that needs to be transferred
# @param amount - Amount of funds to transfer from this contract
@external
func transfer_from{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount : felt
) -> ():
    # Check if the caller is trading contract
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (balance_) = balance.read(assetID=assetID_)

    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    )

    with_attr error_message("Caller is not authorized to do transferFrom in account contract."):
        assert caller = trading_address
    end

    balance.write(assetID=assetID_, value=balance_ - amount)

    transferred_from.emit(asset_id=assetID_, amount=amount)
    return ()
end

# @notice External function called by the ABR Payment contract
# @param collateral_id_ - Collateral ID of the position
# @param market_id_ - Market ID of the position
# @param amount - Amount of funds to transfer from this contract
@external
func transfer_from_abr{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    collateral_id_ : felt, market_id_ : felt, amount_ : felt
):
    # Check if the caller is ABR Payment
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (abr_payment_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_PAYMENT_INDEX, version=version
    )

    with_attr error_message("Caller is not authorized to do transferFrom in account contract."):
        assert caller = abr_payment_address
    end

    # Reduce the amount from balance
    let (balance_) = balance.read(assetID=collateral_id_)
    balance.write(assetID=collateral_id_, value=balance_ - amount_)

    # Update the timestamp of last called
    let (block_timestamp) = get_block_timestamp()
    last_updated.write(market_id=market_id_, value=block_timestamp)

    transferred_from_abr.emit(market_id=market_id_, amount=amount_, timestamp=block_timestamp)
    return ()
end

# @notice External function called by the ABR Payment contract
# @param collateral_id_ - Collateral ID of the position
# @param market_id_ - Market ID of the position
# @param amount_ - Amount of funds to transfer from this contract
@external
func transfer_abr{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    collateral_id_ : felt, market_id_ : felt, amount_ : felt
):
    # Check if the caller is trading contract
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (abr_payment_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_PAYMENT_INDEX, version=version
    )
    with_attr error_message("Caller is not authorized to do transfer in account contract."):
        assert caller = abr_payment_address
    end

    # Add amount to balance
    let (balance_) = balance.read(assetID=collateral_id_)
    balance.write(assetID=collateral_id_, value=balance_ + amount_)

    # Update the timestamp of last called
    let (block_timestamp) = get_block_timestamp()
    last_updated.write(market_id=market_id_, value=block_timestamp)

    transferred_abr.emit(market_id=market_id_, amount=amount_, timestamp=block_timestamp)
    return ()
end

# @notice External function called by the ABR Contract to get the array of net positions of the user
# @returns net_positions_array_len - Length of the array
# @returns net_positions_array - Required array of net positions
@external
func get_net_positions{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    net_positions_array_len : felt, net_positions_array : NetPositions*
):
    alloc_locals

    let (net_positions_array : NetPositions*) = alloc()
    let (array_len : felt) = index_to_market_array_len.read()
    return populate_net_positions(
        net_positions_array_len_=0, net_positions_array_=net_positions_array, final_len_=array_len
    )
end

# @notice External function called by the Liquidate Contract to get the array of net positions of the user
# @returns positions_array_len - Length of the array
# @returns positions_array - Required array of positions
@external
func get_positions{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    positions_array_len : felt, positions_array : PositionDetailsWithMarket*
):
    alloc_locals

    let (positions_array : PositionDetailsWithMarket*) = alloc()
    let (array_len : felt) = index_to_market_array_len.read()
    return populate_positions(
        positions_array_len_=0, positions_array_=positions_array, iterator_=0, final_len_=array_len
    )
end

# @notice External function called by the Trading Contract to transfer funds from account contract
# @param assetID_ - asset ID of the collateral that needs to be transferred
# @param amount - Amount of funds to transfer to this contract
@external
func transfer{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount : felt
) -> ():
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    )
    with_attr error_message(
            "Trading contract is not authorized to do transfer in account contract."):
        assert caller = trading_address
    end

    with_attr error_message("Amount supplied shouldn't be negative in account contract."):
        assert_nn(amount)
    end

    let (balance_) = balance.read(assetID=assetID_)
    balance.write(assetID=assetID_, value=balance_ + amount)

    transferred.emit(asset_id=assetID_, amount=amount)
    return ()
end

# @notice Function called by Trading Contract
# @param request - Details of the order to be executed
# @param signature - Details of the signature
# @param size - Size of the Order to be executed
# @param execution_price - Price at which the order should be executed
# @param amount - TODO: Amount of funds that user must send/receive
# @return 1, if executed correctly
@external
func execute_order{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(
    request : OrderRequest,
    signature : Signature,
    size : felt,
    execution_price : felt,
    margin_amount : felt,
    borrowed_amount : felt,
    market_id : felt,
) -> (res : felt):
    alloc_locals
    let (__fp__, _) = get_fp_and_pc()

    # Make sure that the caller is the authorized Trading Contract
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    )
    with_attr error_message(
            "Trading contract is not authorized to execute order in account contract."):
        assert caller = trading_address
    end

    # hash the parameters
    let (hash) = hash_order(&request)

    # check if signed by the user/liquidator
    is_valid_signature_order(hash, signature, request.liquidatorAddress)

    # Get the details of the position
    let (position_details : PositionDetails) = position_mapping.read(
        marketID=market_id, direction=request.direction
    )

    # Get the portion executed details if already exists
    let (order_portion_executed) = portion_executed.read(orderID=request.orderID)
    let (new_position_executed) = Math64x61_add(order_portion_executed, size)

    # Return if the position size after the executing the current order is more than the order's positionSize
    with_attr error_message(
            "portion executed + size should be less than position in account contract."):
        assert_le(new_position_executed, request.positionSize)
    end

    # Update the portion executed
    portion_executed.write(orderID=request.orderID, value=new_position_executed)

    # closeOrder == 0 -> Open a new position
    # closeOrder == 1 -> Close a position
    if request.closeOrder == 0:
        if position_details.position_size == 0:
            add_to_market_array(market_id)
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        else:
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        end

        # New position size
        let (new_position_size) = Math64x61_add(position_details.position_size, size)

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr

        # New leverage
        let total_value = margin_amount + borrowed_amount
        let (new_leverage) = Math64x61_div(total_value, margin_amount)

        # Create a new struct with the updated details
        let updated_position = PositionDetails(
            avg_execution_price=execution_price,
            position_size=new_position_size,
            margin_amount=margin_amount,
            borrowed_amount=borrowed_amount,
            leverage=new_leverage,
        )

        # Write to the mapping
        position_mapping.write(
            marketID=market_id, direction=request.direction, value=updated_position
        )
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
        tempvar ecdsa_ptr : SignatureBuiltin* = ecdsa_ptr
    else:
        local parent_direction

        if request.direction == LONG:
            assert parent_direction = SHORT
        else:
            assert parent_direction = LONG
        end

        # Get the parent position details
        let (parent_position_details) = position_mapping.read(
            marketID=market_id, direction=parent_direction
        )
        let (new_position_size) = Math64x61_sub(parent_position_details.position_size, size)

        # Assert that the parent position is open
        with_attr error_message("The parent position size is 0"):
            assert_not_zero(parent_position_details.position_size)
        end

        # Assert that the size amount can be closed from the parent position
        with_attr error_message("The size of close order is more than the portionExecuted"):
            assert_nn(new_position_size)
        end

        # Calculate the new leverage if it's a deleveraging order
        local new_leverage

        # Check if it's liq/delveraging order
        let (is_liq) = is_le(2, request.orderType)

        if is_liq == 1:
            # If it's not a normal order, check if it satisfies the conditions to liquidate/deleverage
            let (
                liq_market_id, liq_direction, liq_amount
            ) = get_deleveragable_or_liquidatable_position()

            with_attr error_message("The position not marked to be deleveraged/liquidated"):
                assert liq_market_id = market_id
                assert liq_direction = parent_direction
            end

            with_attr error_message("The size of order should be less than the marked one"):
                assert_le(size, liq_amount)
            end

            let updated_amount = liq_amount - size

            # to64x61(0.0000000001) = 230584300. We are comparing result with this number to fix overflow issues
            let (result) = is_le(updated_amount, 230584300)

            local amount_to_be_updated
            if result == TRUE:
                amount_to_be_updated = 0
            else:
                amount_to_be_updated = updated_amount
            end

            # Create a struct with the updated details
            let updated_liquidatable_position : LiquidatablePosition = LiquidatablePosition(
                market_id=market_id,
                direction=parent_direction,
                amount_to_be_sold=amount_to_be_updated,
            )

            # Update the Liquidatable position
            deleveragable_or_liquidatable_position.write(value=updated_liquidatable_position)

            # If it's a deleveraging order, calculate the new leverage
            if request.orderType == DELEVERAGING_ORDER:
                let total_value = margin_amount + borrowed_amount
                let (leverage_) = Math64x61_div(total_value, margin_amount)
                new_leverage = leverage_
            end
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        else:
            new_leverage = parent_position_details.leverage
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        end

        # Create a new struct with the updated details
        let updated_position = PositionDetails(
            avg_execution_price=execution_price,
            position_size=new_position_size,
            margin_amount=margin_amount,
            borrowed_amount=borrowed_amount,
            leverage=new_leverage,
        )

        if new_position_size == 0:
            if position_details.position_size == 0:
                remove_from_market_array(market_id)
                tempvar syscall_ptr = syscall_ptr
                tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                tempvar range_check_ptr = range_check_ptr
            else:
                tempvar syscall_ptr = syscall_ptr
                tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                tempvar range_check_ptr = range_check_ptr
            end
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        else:
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        end

        # Write to the mapping
        position_mapping.write(
            marketID=market_id, direction=parent_direction, value=updated_position
        )
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
        tempvar ecdsa_ptr : SignatureBuiltin* = ecdsa_ptr
    end
    return (1)
end

# @notice function to update l1 fee and node operators l1 wallet address
# @param request_id_ - Id of the withdrawal request
@external
func update_withdrawal_history{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(request_id_ : felt):
    alloc_locals
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get asset contract address
    let (withdrawal_request_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=WithdrawalRequest_INDEX, version=version
    )

    with_attr error_message("Caller is not authorized to update withdrawal history"):
        assert caller = withdrawal_request_address
    end

    let (arr_len) = withdrawal_history_array_len.read()
    let (index) = find_index_to_be_updated_recurse(request_id_, arr_len)
    local index_to_be_updated = index
    if index_to_be_updated != -1:
        let (history) = withdrawal_history_array.read(index=index_to_be_updated)
        let (registry) = registry_address.read()
        let (version) = contract_version.read()
        # Get asset contract address
        let (asset_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=Asset_INDEX, version=version
        )
        let (asset : Asset) = IAsset.getAsset(
            contract_address=asset_address, id=history.collateral_id
        )
        tempvar decimal = asset.token_decimal

        let (ten_power_decimal) = pow(10, decimal)
        let (decimal_in_64x61_format) = Math64x61_fromFelt(ten_power_decimal)

        let (temp_amount_in_64x61_format) = Math64x61_fromFelt(history.amount)
        let (amount_in_64x61_format) = Math64x61_div(
            temp_amount_in_64x61_format, decimal_in_64x61_format
        )

        let updated_history = WithdrawalHistory(
            request_id=history.request_id,
            collateral_id=history.collateral_id,
            amount=amount_in_64x61_format,
            timestamp=history.timestamp,
            node_operator_L2_address=history.node_operator_L2_address,
            fee=history.fee,
            status=1,
        )
        withdrawal_history_array.write(index=index_to_be_updated, value=updated_history)
        return ()
    end
    return ()
end

# @notice Function to withdraw funds
# @param request_id_ - Id of the withdrawal request
# @param collateral_id_ - Id of the collateral on which user submitted withdrawal request
# @param amount_ - Amount of funds that user wants to withdraw
# @param sig_r_ - R part of signature
# @param sig_s_ - S part of signature
# @param node_operator_L2_address_ - Node operators L2 address
@external
func withdraw{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(
    request_id_ : felt,
    collateral_id_ : felt,
    amount_ : felt,
    sig_r_ : felt,
    sig_s_ : felt,
    node_operator_L2_address_ : felt,
):
    alloc_locals
    let (__fp__, _) = get_fp_and_pc()

    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (signature_ : felt*) = alloc()
    assert signature_[0] = sig_r_
    assert signature_[1] = sig_s_

    # Create withdrawal request for hashing
    local hash_withdrawal_request_ : WithdrawalRequestForHashing = WithdrawalRequestForHashing(
        request_id=request_id_,
        collateral_id=collateral_id_,
        amount=amount_,
        )

    # hash the parameters
    let (hash) = hash_withdrawal_request(&hash_withdrawal_request_)

    # check if Tx is signed by the user
    is_valid_signature(hash, 2, signature_)

    let (arr_len) = withdrawal_history_array_len.read()
    let (result) = check_for_withdrawal_replay(request_id_, arr_len)
    with_attr error_message("Same withdrawal request exists"):
        assert_nn(result)
    end

    # Make sure 'amount' is positive.
    assert_nn(amount_)

    # get L2 Account contract address
    let (user_l2_address) = get_contract_address()

    # Update the fees to be paid by user in withdrawal fee balance contract
    let (withdrawal_fee_balance_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=WithdrawalFeeBalance_INDEX, version=version
    )
    let (standard_fee, fee_collateral_id) = IWithdrawalFeeBalance.get_standard_withdraw_fee(
        contract_address=withdrawal_fee_balance_address
    )

    # Compute current balance
    let (fee_collateral_balance) = balance.read(assetID=fee_collateral_id)
    with_attr error_message(
            "Fee amount should be less than or equal to the fee collateral balance"):
        assert_le(standard_fee, fee_collateral_balance)
    end
    tempvar new_fee_collateral_balance = fee_collateral_balance - standard_fee

    # Update the new fee collateral balance
    balance.write(assetID=fee_collateral_id, value=new_fee_collateral_balance)

    IWithdrawalFeeBalance.update_withdrawal_fee_mapping(
        contract_address=withdrawal_fee_balance_address,
        user_l2_address_=user_l2_address,
        collateral_id_=fee_collateral_id,
        fee_to_add_=standard_fee,
    )

    # Compute current balance
    let (current_balance) = balance.read(assetID=collateral_id_)
    with_attr error_message("Withdrawal amount requested should be less than balance"):
        assert_le(amount_, current_balance)
    end
    tempvar new_balance = current_balance - amount_

    # Update the new balance
    balance.write(assetID=collateral_id_, value=new_balance)

    # Calculate the timestamp
    let (timestamp_) = get_block_timestamp()

    # Get asset contract address
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    )
    # Reading token decimal field of an asset
    let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=collateral_id_)
    tempvar decimal = asset.token_decimal
    tempvar ticker = asset.ticker

    let (ten_power_decimal) = pow(10, decimal)
    let (decimal_in_64x61_format) = Math64x61_fromFelt(ten_power_decimal)

    let (amount_times_ten_power_decimal) = Math64x61_mul(amount_, decimal_in_64x61_format)
    let (amount_in_felt) = Math64x61_toFelt(amount_times_ten_power_decimal)

    # Get the L1 wallet address of the user
    let (user_l1_address) = L1_address.read()

    # Add Withdrawal Request to WithdrawalRequest Contract
    let (withdrawal_request_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=WithdrawalRequest_INDEX, version=version
    )
    IWithdrawalRequest.add_withdrawal_request(
        contract_address=withdrawal_request_address,
        request_id_=request_id_,
        user_l1_address_=user_l1_address,
        ticker_=ticker,
        amount_=amount_in_felt,
    )

    # Create a withdrawal history object
    local withdrawal_history_ : WithdrawalHistory = WithdrawalHistory(
        request_id=request_id_,
        collateral_id=collateral_id_,
        amount=amount_in_felt,
        timestamp=timestamp_,
        node_operator_L2_address=node_operator_L2_address_,
        fee=standard_fee,
        status=0
        )

    # Update Withdrawal history
    let (array_len) = withdrawal_history_array_len.read()
    withdrawal_history_array.write(index=array_len, value=withdrawal_history_)
    withdrawal_history_array_len.write(array_len + 1)

    withdrawal_request.emit(
        collateral_id=collateral_id_, amount=amount_, node_operator_l2=node_operator_L2_address_
    )
    return ()
end

# @notice Function called by liquidate contract to mark the position as liquidated/deleveraged
# @param position_ - Order Id of the position to be marked
# @param amount_to_be_sold_ - Amount to be put on sale for deleveraging a position
@external
func liquidate_position{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    position_ : PositionDetailsWithMarket, amount_to_be_sold_ : felt
):
    alloc_locals

    # Check if the caller is the liquidator contract
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (liquidate_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Liquidate_INDEX, version=version
    )

    with_attr error_message("Only liquidate contract is allowed to call for liquidation"):
        assert caller = liquidate_address
    end

    let liquidatable_position : LiquidatablePosition = LiquidatablePosition(
        market_id=position_.market_id,
        direction=position_.direction,
        amount_to_be_sold=amount_to_be_sold_,
    )

    # Update deleveraged or liquidatable position
    deleveragable_or_liquidatable_position.write(value=liquidatable_position)

    liquidate_deleverage.emit(
        market_id=position_.market_id,
        direction=position_.direction,
        amount_to_be_sold=amount_to_be_sold_,
    )
    return ()
end

######################
# Internal Functions #
######################

# @notice Internal Function called by get_withdrawal_history to recursively add WithdrawalRequest to the array and return it
# @param withdrawal_list_len_ - Stores the current length of the populated withdrawals array
# @param withdrawal_list_ - Array of WithdrawalRequest filled up to the index
# @return withdrawal_list_len - Length of the withdrawal_list
# @return withdrawal_list - Fully populated list of Withdrawals
func populate_withdrawals_array{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    withdrawal_list_len_ : felt, withdrawal_list_ : WithdrawalHistory*
) -> (withdrawal_list_len : felt, withdrawal_list : WithdrawalHistory*):
    let (withdrawal_history) = withdrawal_history_array.read(index=withdrawal_list_len_)

    if withdrawal_history.collateral_id == 0:
        return (withdrawal_list_len_, withdrawal_list_)
    end

    assert withdrawal_list_[withdrawal_list_len_] = withdrawal_history
    return populate_withdrawals_array(withdrawal_list_len_ + 1, withdrawal_list_)
end

# @notice Internal Function called by return_array_collaterals to recursively add collateralBalance to the array and return it
# @param array_list_len_ - Stores the current length of the populated array
# @param array_list_ - Array of CollateralBalance filled up to the index
# @return array_list_len - Length of the array_list
# @return array_list - Fully populated list of CollateralBalance
func populate_array_collaterals{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    array_list_len_ : felt, array_list_ : CollateralBalance*, final_len_ : felt
) -> (array_list_len : felt, array_list : CollateralBalance*):
    if array_list_len_ == final_len_:
        return (array_list_len_, array_list_)
    end

    let (collateral_id) = collateral_array.read(index=array_list_len_)
    let (collateral_balance : felt) = balance.read(assetID=collateral_id)
    let collateral_balance_struct = CollateralBalance(
        assetID=collateral_id, balance=collateral_balance
    )

    assert array_list_[array_list_len_] = collateral_balance_struct
    return populate_array_collaterals(array_list_len_ + 1, array_list_, final_len_)
end

# @notice Internal Function called by get_positions to recursively add active positions to the array and return it
# @param positions_array_len_ - Length of the array
# @param positions_array_ - Required array of positions
# @param iterator_ - Current length of traversed array
# @param final_len_ - Length of the final array
# @returns positions_array_len - Length of the positions array
# @returns positions_array - Array with the positions
func populate_positions{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    positions_array_len_ : felt,
    positions_array_ : PositionDetailsWithMarket*,
    iterator_ : felt,
    final_len_ : felt,
) -> (positions_array_len : felt, positions_array : PositionDetailsWithMarket*):
    alloc_locals

    # If we reached the end of the array, then return
    if final_len_ == iterator_:
        return (positions_array_len_, positions_array_)
    end

    # Get the market id at that position
    let (curr_market_id : felt) = index_to_market_array.read(index=iterator_)

    # Get Long position
    let (long_position : PositionDetails) = position_mapping.read(
        marketID=curr_market_id, direction=LONG
    )

    # Get Short position
    let (short_position : PositionDetails) = position_mapping.read(
        marketID=curr_market_id, direction=SHORT
    )

    local is_long
    local is_short

    if long_position.position_size == 0:
        assert is_long = 0
    else:
        # Store it in the array
        let curr_position = PositionDetailsWithMarket(
            market_id=curr_market_id,
            direction=LONG,
            avg_execution_price=long_position.avg_execution_price,
            position_size=long_position.position_size,
            margin_amount=long_position.margin_amount,
            borrowed_amount=long_position.borrowed_amount,
            leverage=long_position.leverage,
        )
        assert positions_array_[positions_array_len_] = curr_position
        assert is_long = 1
    end

    if short_position.position_size == 0:
        assert is_short = 0
    else:
        # Store it in the array
        let curr_position = PositionDetailsWithMarket(
            market_id=curr_market_id,
            direction=SHORT,
            avg_execution_price=short_position.avg_execution_price,
            position_size=short_position.position_size,
            margin_amount=short_position.margin_amount,
            borrowed_amount=short_position.borrowed_amount,
            leverage=short_position.leverage,
        )
        assert positions_array_[positions_array_len_ + is_long] = curr_position
        assert is_short = 1
    end

    return populate_positions(
        positions_array_len_=positions_array_len_ + is_long + is_short,
        positions_array_=positions_array_,
        iterator_=iterator_ + 1,
        final_len_=final_len_,
    )
end

# @notice External function called by the ABR Contract to get the array of net positions of the user
# @param net_positions_array_len_ - Length of the array
# @param net_positions_array_ - Required array of net positions
# @param final_len_ - Length of the final array
# @returns net_positions_array_len - Length of the net positions array
# @returns net_positions_array - Array with the net positions
func populate_net_positions{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    net_positions_array_len_ : felt, net_positions_array_ : NetPositions*, final_len_ : felt
) -> (net_positions_array_len : felt, net_positions_array : NetPositions*):
    # If reached the end of the array, then return
    if net_positions_array_len_ == final_len_:
        return (net_positions_array_len_, net_positions_array_)
    end

    # Get the market id at that position
    let (curr_market_id : felt) = index_to_market_array.read(index=net_positions_array_len_)

    # Get Long position
    let (long_position : PositionDetails) = position_mapping.read(
        marketID=curr_market_id, direction=LONG
    )

    # Get Short position
    let (short_position : PositionDetails) = position_mapping.read(
        marketID=curr_market_id, direction=SHORT
    )

    # Calculate the net position
    let (net_size : felt) = Math64x61_sub(long_position.position_size, short_position.position_size)

    # Create the struct with the details
    let net_position_struct : NetPositions = NetPositions(
        market_id=curr_market_id, position_size=net_size
    )

    # Store it in the array
    assert net_positions_array_[net_positions_array_len_] = net_position_struct

    # Recursively call the next market_id
    return populate_net_positions(
        net_positions_array_len_=net_positions_array_len_ + 1,
        net_positions_array_=net_positions_array_,
        final_len_=final_len_,
    )
end

# @notice Internal function to hash the order parameters
# @param orderRequest - Struct of order request to hash
# @param res - Hash of the details
func hash_order{pedersen_ptr : HashBuiltin*}(orderRequest : OrderRequest*) -> (res : felt):
    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (hash_state_ptr) = hash_init()
        let (hash_state_ptr) = hash_update(hash_state_ptr, orderRequest, 10)
        let (res) = hash_finalize(hash_state_ptr)
        let pedersen_ptr = hash_ptr
        return (res=res)
    end
end

# @notice Internal function to hash the withdrawal request parameters
# @param withdrawal_request_ - Struct of withdrawal Request to hash
# @param res - Hash of the details
func hash_withdrawal_request{pedersen_ptr : HashBuiltin*}(
    withdrawal_request_ : WithdrawalRequestForHashing*
) -> (res : felt):
    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (hash_state_ptr) = hash_init()
        let (hash_state_ptr) = hash_update(hash_state_ptr, withdrawal_request_, 3)
        let (res) = hash_finalize(hash_state_ptr)
        let pedersen_ptr = hash_ptr
        return (res=res)
    end
end

# @notice Internal function to add a market to the array
# @param market_id - Id of the market to tbe added
# @return 1 - If successfully added
func add_to_market_array{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id : felt
):
    let (is_exists) = market_is_exist.read(market_id=market_id)

    if is_exists == TRUE:
        return ()
    end

    let (arr_len) = index_to_market_array_len.read()
    index_to_market_array.write(index=arr_len, value=market_id)

    market_to_index_mapping.write(market_id=market_id, value=arr_len)
    index_to_market_array_len.write(value=arr_len + 1)
    market_is_exist.write(market_id=market_id, value=TRUE)
    return ()
end

# @notice Internal function called to remove a market_id when both positions are fully closed
# @param market_id - Id of the market
# @return 1 - If successfully removed
func remove_from_market_array{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id : felt
):
    alloc_locals

    let (index) = market_to_index_mapping.read(market_id=market_id)
    let (arr_len) = index_to_market_array_len.read()

    if arr_len == 1:
        index_to_market_array.write(index=index, value=0)
    else:
        let (last_id) = index_to_market_array.read(index=arr_len - 1)
        index_to_market_array.write(index=index, value=last_id)
        index_to_market_array.write(index=arr_len - 1, value=0)
        market_to_index_mapping.write(market_id=last_id, value=index)
    end

    market_to_index_mapping.write(market_id=market_id, value=0)
    market_is_exist.write(market_id=market_id, value=FALSE)
    index_to_market_array_len.write(arr_len - 1)
    return ()
end

# @notice Internal function to add collateral to the array
# @param new_asset_id - asset Id to be added
# @param iterator - index at which an asset to be added
# @param length - length of collateral array
func add_collateral{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    new_asset_id : felt, iterator : felt, length : felt
) -> (res : felt):
    alloc_locals
    if iterator == length:
        collateral_array.write(index=iterator, value=new_asset_id)
        collateral_array_len.write(iterator + 1)
        return (1)
    end

    let (collateral_id) = collateral_array.read(index=iterator)
    local difference = collateral_id - new_asset_id
    if difference == 0:
        return (0)
    end

    return add_collateral(new_asset_id=new_asset_id, iterator=iterator + 1, length=length)
end

# @notice Internal function to recursively find the index of the withdrawal history to be updated
# @param request_id_ - Id of the withdrawal request
# @param arr_len_ - current index which is being checked to be updated
# @return index - returns the index which needs to be updated
func find_index_to_be_updated_recurse{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr
}(request_id_ : felt, arr_len_ : felt) -> (index : felt):
    if arr_len_ == 0:
        return (-1)
    end

    let (request : WithdrawalHistory) = withdrawal_history_array.read(index=arr_len_ - 1)
    if request.request_id == request_id_:
        return (arr_len_ - 1)
    end

    return find_index_to_be_updated_recurse(request_id_, arr_len_ - 1)
end

# @notice Internal function to recursively check for withdrawal replays
# @param request_id_ - Id of the withdrawal request
# @param arr_len_ - current index which is being checked to be updated
# @return - -1 if same withdrawal request already exists, else 1
func check_for_withdrawal_replay{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    request_id_ : felt, arr_len_ : felt
) -> (index : felt):
    if arr_len_ == 0:
        return (1)
    end

    let (request : WithdrawalHistory) = withdrawal_history_array.read(index=arr_len_ - 1)
    if request.request_id == request_id_:
        return (-1)
    end

    return check_for_withdrawal_replay(request_id_, arr_len_ - 1)
end
