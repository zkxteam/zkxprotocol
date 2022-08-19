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
    ORDER_CLOSED_PARTIALLY,
    ORDER_CLOSED,
    ORDER_LIQUIDATED,
    ORDER_OPENED_PARTIALLY,
    ORDER_OPENED,
    ORDER_TO_BE_DELEVERAGED,
    ORDER_TO_BE_LIQUIDATED,
    Trading_INDEX,
    WithdrawalFeeBalance_INDEX,
    WithdrawalRequest_INDEX,
)
from contracts.DataTypes import (
    Asset,
    CollateralBalance,
    Message,
    OrderDetails,
    OrderDetailsWithIDs,
    OrderRequest,
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
    Math64x61_div,
    Math64x61_mul
)
from contracts.libraries.Math64x61 import Math64x61

##########
# Events #
##########

# Event emitted whenever collateral is transferred from account by trading
@event
func transferred_from(
    asset_id : felt, amount : felt
):
end

# Event emitted whenever collateral is transferred to account by trading
@event
func transferred(
    asset_id : felt, amount : felt
):
end

# Event emitted whenever collateral is transferred to account by abr payment
@event
func transferred_abr(
    order_id : felt, asset_id : felt, market_id : felt, amount : felt, timestamp : felt
):
end

# Event emitted whenever collateral is transferred from account by abr payment
@event
func transferred_from_abr(
    order_id : felt, asset_id : felt, market_id : felt, amount : felt, timestamp : felt
):
end

# Event emitted whenver a new withdrawal request is made
@event
func withdrawal_request(
    collateral_id : felt, amount : felt, node_operator_l2 : felt
):
end

# Event emitted whenever a position is marked to be liquidated/deleveraged
@event
func liquidate_deleverage(position_id : felt, amount : felt):
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

# Mapping of orderID to the order details
@storage_var
func order_mapping(orderID : felt) -> (res : OrderDetails):
end

# Mapping of orderID to the timestamp of last updated value
@storage_var
func last_updated(order_id) -> (value : felt):
end

# Stores L1 address associated with the account
@storage_var
func L1_address() -> (res : felt):
end

# Stores all positions held by the user
@storage_var
func position_array(index : felt) -> (position_id : felt):
end

# Stores all collaterals held by the user
@storage_var
func collateral_array(index : felt) -> (collateral_id : felt):
end

# Stores length of the position array
@storage_var
func position_array_len() -> (len : felt):
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
func deleveraged_or_liquidatable_position() -> (order_id : felt):
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
func get_order_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    orderID_ : felt
) -> (res : OrderDetails):
    let (res) = order_mapping.read(orderID=orderID_)
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

# @notice view function to get amount to be sold in a position
# @param order_id_ - ID of an order
# @return res - amount to be sold in a position
@view
func get_amount_to_be_sold{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    order_id_ : felt
) -> (res : felt):
    let (res) = amount_to_be_sold.read(order_id=order_id_)
    return (res=res)
end

# @notice view function to get deleveraged or liquidatable position
# @return order_id - Id of an order, amount_to_be_sold - amount to be sold in a position
@view
func get_deleveraged_or_liquidatable_position{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr
}() -> (order_id : felt, amount_to_be_sold : felt):
    let (order_id_) = deleveraged_or_liquidatable_position.read()
    let (order_details) = get_order_data(order_id_)
    if order_details.status == ORDER_TO_BE_DELEVERAGED:
        let (amount) = amount_to_be_sold.read(order_id=order_id_)
        return (order_id=order_id_, amount_to_be_sold=amount)
    else:
        return (order_id=order_id_, amount_to_be_sold=0)
    end
end

# @notice view function to get all the open positions
# @return array_list_len - Length of the array_list
# @return array_list - Fully populated list of OrderDetails
@view
func return_array_positions{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (array_list_len : felt, array_list : OrderDetailsWithIDs*):
    let (array_list : OrderDetailsWithIDs*) = alloc()
    return populate_array_positions(iterator=0, array_list_len=0, array_list=array_list)
end

# @notice view function to get all use collaterals
# @return array_list_len - Length of the array_list
# @return array_list - Fully populated list of CollateralBalance
@view
func return_array_collaterals{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (array_list_len : felt, array_list : CollateralBalance*):
    let (array_list : CollateralBalance*) = alloc()
    return populate_array_collaterals(0, array_list)
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
# @param market_id - ID of a market
# @return res - true if it is complete, else false
@view
func timestamp_check{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    orderID_ : felt
) -> (is_eight_hours : felt):
    alloc_locals
    # Get the latest block
    let (block_timestamp) = get_block_timestamp()

    # Fetch the last updated time
    let (last_call) = last_updated.read(order_id=orderID_)

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
    let (amount_in_decimal_representation) = Math64x61.from_decimal_felt(amount, decimals=asset.token_decimal)

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

    deposited.emit(asset_id = assetID_, amount = amount_in_decimal_representation)
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

    transferred_from.emit(asset_id = assetID_, amount = amount)
    return ()
end

# @notice External function called by the ABR Payment contract
# @param orderID_ - Order Id of the position
# @param assetID_ - asset ID of the collateral that needs to be transferred
# @param marketID_ - market ID of the position
# @param amount - Amount of funds to transfer from this contract
@external
func transfer_from_abr{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    orderID_ : felt, assetID_ : felt, marketID_ : felt, amount : felt
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
    let (balance_) = balance.read(assetID=assetID_)
    balance.write(assetID=assetID_, value=balance_ - amount)

    # Update the timestamp of last called
    let (block_timestamp) = get_block_timestamp()
    last_updated.write(order_id = orderID_, value=block_timestamp)

    transferred_from_abr.emit(order_id = orderID_, asset_id = assetID_, market_id = marketID_, amount = amount, timestamp = block_timestamp)
    return ()
end

# @notice External function called by the ABR Payment contract
# @param orderID_ - Order Id of the position
# @param assetID_ - asset ID of the collateral that needs to be transferred
# @param marketID_ - market ID of the position
# @param amount - Amount of funds to transfer from this contract
@external
func transfer_abr{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    orderID_ : felt, assetID_ : felt, marketID_ : felt, amount : felt
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
    let (balance_) = balance.read(assetID=assetID_)
    balance.write(assetID=assetID_, value=balance_ + amount)

    # Update the timestamp of last called
    let (block_timestamp) = get_block_timestamp()
    last_updated.write(order_id = orderID_, value=block_timestamp)

    transferred_abr.emit(order_id = orderID_, asset_id = assetID_, market_id = marketID_, amount = amount, timestamp = block_timestamp)
    return ()
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

    transferred.emit(asset_id = assetID_, amount = amount)
    return ()
end

# #### TODO: Remove; Only for testing purposes #####
@external
func set_balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount_ : felt
):
    let (curr_balance) = get_balance(assetID_)
    balance.write(assetID=assetID_, value=amount_)
    let (array_len) = collateral_array_len.read()

    if curr_balance == 0:
        add_collateral(new_asset_id=assetID_, iterator=0, length=array_len)
        return()
    else:
        return()
    end
end

# @notice External function called to remove a fully closed position
# @param id_ - Index of the element in the array
# @return 1 - If successfully removed
@external
func remove_from_array{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt
) -> (res : felt):
    alloc_locals

    let (pos_id) = position_array.read(index=id_)
    if pos_id == 0:
        with_attr error_message("No order exists in that index"):
            assert 1 = 0
        end
    end

    let (posDetails : OrderDetails) = order_mapping.read(orderID=pos_id)

    with_attr error_message("The order is not fully closed yet."):
        assert posDetails.status = ORDER_CLOSED
    end

    let (arr_len) = position_array_len.read()
    let (last_id) = position_array.read(index=arr_len - 1)

    position_array.write(index=id_, value=last_id)
    position_array.write(index=arr_len - 1, value=0)

    position_array_len.write(arr_len - 1)
    return (1)
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

    local status_
    # closeOrder == 0 -> Open a new position
    # closeOrder == 1 -> Close a position
    if request.closeOrder == 0:
        # Get the order details if already exists
        let (orderDetails) = order_mapping.read(orderID=request.orderID)
        # If it's a new order
        if orderDetails.assetID == 0:
            # Create if the order is being fully opened
            # status_ == 1, partially opened; ORDER_OPENED_PARTIALLY
            # status_ == 2, fully opened; ORDER_OPENED
            if request.positionSize == size:
                assert status_ = ORDER_OPENED
            else:
                assert status_ = ORDER_OPENED_PARTIALLY
            end

            # Create a new struct with the updated details
            let new_order = OrderDetails(
                assetID=request.assetID,
                collateralID=request.collateralID,
                price=request.price,
                executionPrice=execution_price,
                positionSize=request.positionSize,
                orderType=request.orderType,
                direction=request.direction,
                portionExecuted=size,
                status=status_,
                marginAmount=margin_amount,
                borrowedAmount=borrowed_amount,
                leverage=request.leverage,
            )
            # Write to the mapping
            order_mapping.write(orderID=request.orderID, value=new_order)

            add_to_array(request.orderID)
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
            tempvar ecdsa_ptr : SignatureBuiltin* = ecdsa_ptr
            # If it's an existing order
        else:
            # Return if the position size after the executing the current order is more than the order's positionSize
            let (size_by_leverage) = Math64x61_mul(size, request.leverage)
            with_attr error_message(
                    "Paritally executed + remaining should be less than position in account contract."):
                assert_le(size + orderDetails.portionExecuted, request.positionSize)
            end

            # Check if the order is in the process of being closed or if it was deleveraged
            if orderDetails.status == ORDER_TO_BE_DELEVERAGED:
                tempvar range_check_ptr = range_check_ptr
            else:
                assert_le(orderDetails.status, ORDER_CLOSED_PARTIALLY)
                tempvar range_check_ptr = range_check_ptr
            end

            # Check if the order is fully filled by executing the current one
            if request.positionSize == size + orderDetails.portionExecuted:
                status_ = ORDER_OPENED
            else:
                status_ = ORDER_OPENED_PARTIALLY
            end

            # Create a new struct with the updated details
            let updated_order = OrderDetails(
                assetID=orderDetails.assetID,
                collateralID=orderDetails.collateralID,
                price=orderDetails.price,
                executionPrice=execution_price,
                positionSize=orderDetails.positionSize,
                orderType=request.orderType,
                direction=orderDetails.direction,
                portionExecuted=orderDetails.portionExecuted + size,
                status=status_,
                marginAmount=margin_amount,
                borrowedAmount=borrowed_amount,
                leverage=request.leverage,
            )
            # Write to the mapping
            order_mapping.write(orderID=request.orderID, value=updated_order)
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
            tempvar ecdsa_ptr : SignatureBuiltin* = ecdsa_ptr
        end
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
        tempvar ecdsa_ptr : SignatureBuiltin* = ecdsa_ptr
    else:
        # Get the order details
        let (orderDetails) = order_mapping.read(orderID=request.parentOrder)

        # Assert that it's the reverse direction of the current position
        with_attr error_message("The close order must have opposite direction of open order"):
            assert_not_equal(request.direction, orderDetails.direction)
        end

        # Assert that the order exists
        with_attr error_message("The open order doesn't exist"):
            assert_not_zero(orderDetails.positionSize)
        end

        with_attr error_message("The size of close order is more than the portionExecuted"):
            assert_nn(orderDetails.portionExecuted - size)
        end

        local new_leverage
        if request.orderType == DELEVERAGING_ORDER:
            let total_value = margin_amount + borrowed_amount
            let (leverage_) = Math64x61_div(total_value, margin_amount)
            new_leverage = leverage_
        else:
            new_leverage = request.leverage
        end
        tempvar range_check_ptr = range_check_ptr

        # Check if the order is fully closed or not
        # status_ == 4, fully closed; ORDER_CLOSED
        # status_ == 3, partially closed; ORDER_CLOSED_PARTIALLY
        # status_ == 5, toBeDeleveraged; ORDER_TO_BE_DELEVERAGED
        # status_ == 6, toBeLiquidated; ORDER_TO_BE_LIQUIDATED
        # status_ == 7, fullyLiquidated; ORDER_LIQUIDATED
        if orderDetails.portionExecuted - size == 0:
            if request.orderType == LIQUIDATION_ORDER:
                assert status_ = ORDER_LIQUIDATED
            else:
                assert status_ = ORDER_CLOSED
            end
        else:
            if request.orderType == DELEVERAGING_ORDER:
                assert status_ = ORDER_TO_BE_DELEVERAGED
            else:
                if request.orderType == LIQUIDATION_ORDER:
                    assert status_ = ORDER_TO_BE_LIQUIDATED
                else:
                    assert status_ = ORDER_CLOSED_PARTIALLY
                end
            end
        end

        # Update the amount to be sold after deleveraging
        if orderDetails.status == ORDER_TO_BE_DELEVERAGED:
            let (amount) = amount_to_be_sold.read(order_id=request.parentOrder)
            let updated_amount = amount - size
            let (positive_updated_amount) = abs_value(updated_amount)
            # to64x61(0.0000000001) = 230584300. We are comparing result with this number to fix overflow issues
            let (result) = is_le(updated_amount, 230584300)
            local amount_to_be_updated
            if result == TRUE:
                amount_to_be_updated = 0
            else:
                amount_to_be_updated = updated_amount
            end
            amount_to_be_sold.write(order_id=request.parentOrder, value=amount_to_be_updated)
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        else:
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        end

        # Create a new struct with the updated details
        let updated_order = OrderDetails(
            assetID=orderDetails.assetID,
            collateralID=orderDetails.collateralID,
            price=orderDetails.price,
            executionPrice=orderDetails.executionPrice,
            positionSize=orderDetails.positionSize - size,
            orderType=orderDetails.orderType,
            direction=orderDetails.direction,
            portionExecuted=orderDetails.portionExecuted - size,
            status=status_,
            marginAmount=margin_amount,
            borrowedAmount=borrowed_amount,
            leverage=new_leverage,
        )

        # Write to the mapping
        order_mapping.write(orderID=request.parentOrder, value=updated_order)
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
        let (amount_in_64x61_format) = Math64x61.from_decimal_felt(history.amount, decimals=asset.token_decimal)

        let updated_history = WithdrawalHistory(
            request_id=history.request_id,
            collateral_id=history.collateral_id,
            amount=amount_in_64x61_format,
            timestamp=history.timestamp,
            node_operator_L2_address=history.node_operator_L2_address,
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
    with_attr error_message("Fee amount should be less than or equal to the fee collateral balance"):
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
    # Converting amount to felt representation
    let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=collateral_id_)
    let (amount_in_felt) = Math64x61.to_decimal_felt(amount_, decimals=asset.token_decimal)
    tempvar ticker = asset.ticker

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
        status=0
        )

    # Update Withdrawal history
    let (array_len) = withdrawal_history_array_len.read()
    withdrawal_history_array.write(index=array_len, value=withdrawal_history_)
    withdrawal_history_array_len.write(array_len + 1)

    withdrawal_request.emit(collateral_id = collateral_id_, amount = amount_, node_operator_l2 = node_operator_L2_address_)
    return ()
end

# @notice Function called by liquidate contract to mark the position as liquidated/deleveraged
# @param id_ - Order Id of the position to be marked
# @param amount_to_be_sold_ - Amount to be put on sale for deleveraging a position
@external
func liquidate_position{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt, amount_to_be_sold_ : felt
):
    alloc_locals

    let (order_details : OrderDetails) = order_mapping.read(orderID=id_)

    with_attr error_message("Amount to be sold cannot be negative"):
        assert_nn(amount_to_be_sold_)
    end
    with_attr error_message("Amount to be sold should be less than or equal to the portion executed"):
        assert_le(amount_to_be_sold_, order_details.portionExecuted)
    end

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

    local status_
    if amount_to_be_sold_ == 0:
        status_ = ORDER_TO_BE_LIQUIDATED
    else:
        status_ = ORDER_TO_BE_DELEVERAGED
    end

    # Create a new struct with the updated details by setting toBeLiquidated flag to true
    let updated_order = OrderDetails(
        assetID=order_details.assetID,
        collateralID=order_details.collateralID,
        price=order_details.price,
        executionPrice=order_details.executionPrice,
        positionSize=order_details.positionSize,
        orderType=order_details.orderType,
        direction=order_details.direction,
        portionExecuted=order_details.portionExecuted,
        status=status_,
        marginAmount=order_details.marginAmount,
        borrowedAmount=order_details.borrowedAmount,
        leverage=order_details.leverage,
    )
    # Write to the mapping
    order_mapping.write(orderID=id_, value=updated_order)
    # Update deleveraged or liquidatable position
    deleveraged_or_liquidatable_position.write(value=id_)
    # Update amount_to_be_sold storage variable
    amount_to_be_sold.write(order_id=id_, value=amount_to_be_sold_)

    liquidate_deleverage.emit(position_id = id_, amount = amount_to_be_sold_)
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
    array_list_len_ : felt, array_list_ : CollateralBalance*
) -> (array_list_len : felt, array_list : CollateralBalance*):
    let (collateral_id) = collateral_array.read(index=array_list_len_)

    if collateral_id == 0:
        return (array_list_len_, array_list_)
    end

    let (collateral_balance : felt) = balance.read(assetID=collateral_id)
    let collateral_balance_struct = CollateralBalance(
        assetID=collateral_id, balance=collateral_balance
    )

    assert array_list_[array_list_len_] = collateral_balance_struct
    return populate_array_collaterals(array_list_len_ + 1, array_list_)
end

# @notice Internal Function called by return array to recursively add positions to the array and return it
# @param iterator - Index of the position_array currently pointing to
# @param array_list_len - Stores the current length of the populated array
# @param array_list - Array of OrderRequests filled up to the index
# @return array_list_len - Length of the array_list
# @return array_list - Fully populated list of OrderDetails
func populate_array_positions{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    iterator : felt, array_list_len : felt, array_list : OrderDetailsWithIDs*
) -> (array_list_len : felt, array_list : OrderDetailsWithIDs*):
    let (pos) = position_array.read(index=iterator)

    if pos == 0:
        return (array_list_len, array_list)
    end

    let (pos_details : OrderDetails) = order_mapping.read(orderID=pos)
    let order_details_w_id = OrderDetailsWithIDs(
        orderID=pos,
        assetID=pos_details.assetID,
        collateralID=pos_details.collateralID,
        price=pos_details.price,
        executionPrice=pos_details.executionPrice,
        positionSize=pos_details.positionSize,
        orderType=pos_details.orderType,
        direction=pos_details.direction,
        portionExecuted=pos_details.portionExecuted,
        status=pos_details.status,
        marginAmount=pos_details.marginAmount,
        borrowedAmount=pos_details.borrowedAmount,
    )

    if pos_details.status == ORDER_CLOSED:
        return populate_array_positions(iterator + 1, array_list_len, array_list)
    else:
        if pos_details.status == ORDER_LIQUIDATED:
            return populate_array_positions(iterator + 1, array_list_len, array_list)
        else:
            assert array_list[array_list_len] = order_details_w_id
            return populate_array_positions(iterator + 1, array_list_len + 1, array_list)
        end
    end
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

# @notice Internal function to add a position to the array when it is opened
# @param id_ - OrderRequest Id to be added
# @return 1 - If successfully added
func add_to_array{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id_ : felt
) -> (res : felt):
    let (arr_len) = position_array_len.read()
    position_array.write(index=arr_len, value=id_)
    position_array_len.write(arr_len + 1)
    return (1)
end

# @notice Internal function to add collateral to the array
# @param new_asset_id - asset Id to be added
# @param iterator - index at which an asset to be added
# @param length - length of collateral array
func add_collateral{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    new_asset_id : felt, iterator : felt, length : felt
):
    alloc_locals
    if iterator == length:
        collateral_array.write(index=iterator, value=new_asset_id)
        collateral_array_len.write(iterator + 1)
        return ()
    end

    let (collateral_id) = collateral_array.read(index=iterator)
    local difference = collateral_id - new_asset_id
    if difference == 0:
        return ()
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
