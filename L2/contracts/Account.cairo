%lang starknet
%builtins pedersen range_check ecdsa bitwise

from contracts.DataTypes import (
    Asset,
    CollateralBalance,
    Message,
    MultipleOrder,
    OrderDetails,
    OrderDetailsWithIDs,
    OrderRequest,
    Signature,
    WithdrawalHistory,
)
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IAccount import IAccount
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IWithdrawalFeeBalance import IWithdrawalFeeBalance
from contracts.interfaces.IWithdrawalRequest import IWithdrawalRequest
from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.messages import send_message_to_l1
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.common.syscalls import get_contract_address, get_block_timestamp
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin, BitwiseBuiltin
from starkware.starknet.common.syscalls import call_contract, get_caller_address, get_tx_signature
from starkware.cairo.common.hash_state import (
    hash_init,
    hash_finalize,
    hash_update,
    hash_update_single,
)
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.math import (
    assert_le,
    assert_not_equal,
    assert_not_zero,
    assert_nn,
    abs_value,
)
from starkware.cairo.common.pow import pow
from contracts.Constants import (
    Asset_INDEX,
    Market_INDEX,
    TradingFees_INDEX,
    Holding_INDEX,
    FeeBalance_INDEX,
    LiquidityFund_INDEX,
    InsuranceFund_INDEX,
    AccountRegistry_INDEX,
    ABR_INDEX,
    ABR_FUNDS_INDEX,
    Liquidate_INDEX,
    Trading_INDEX,
    WithdrawalFeeBalance_INDEX,
    WithdrawalRequest_INDEX,
)

from contracts.Math_64x61 import (
    Math64x61_mul,
    Math64x61_div,
    Math64x61_fromFelt,
    Math64x61_toFelt,
    Math64x61_sub,
)

const MESSAGE_WITHDRAW = 0

#
# Storage
#

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of Authorized Registry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# @notice Stores the address of Market contract
@storage_var
func market_address() -> (contract_address : felt):
end

# @notice Stores the address of Market contract
@storage_var
func abr_address() -> (contract_address : felt):
end

@storage_var
func current_nonce() -> (res : felt):
end

@storage_var
func public_key() -> (res : felt):
end

@storage_var
func trading_volume() -> (res : felt):
end

@storage_var
func balance(assetID : felt) -> (res : felt):
end

@storage_var
func order_mapping(orderID : felt) -> (res : OrderDetails):
end

# @notice Mapping of marketID to the timestamp of last updated value
@storage_var
func last_updated(market_id) -> (value : felt):
end

# L1 User associated with the account
@storage_var
func L1_address() -> (res : felt):
end

# Stores L1 ZKX Contract address
@storage_var
func L1_ZKX_address() -> (res : felt):
end

# Store positions to facilitate liquidation request
@storage_var
func position_array(index : felt) -> (position_id : felt):
end

# Stores all collaterals held by the user
@storage_var
func collateral_array(index : felt) -> (collateral_id : felt):
end

# Length of the position array
@storage_var
func position_array_len() -> (len : felt):
end

# Length of the collateral array
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

# Length of the withdrawal history array
@storage_var
func withdrawal_history_array_len() -> (len : felt):
end

#
# Constructor
#

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    public_key_ : felt, registry_address_ : felt, version_ : felt, L1_ZKX_address_ : felt
):
    public_key.write(public_key_)
    registry_address.write(value=registry_address_)
    contract_version.write(value=version_)
    L1_ZKX_address.write(value=L1_ZKX_address_)
    return ()
end

#
# Guards
#

@view
func assert_only_self{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}():
    let (self) = get_contract_address()
    let (caller) = get_caller_address()
    assert self = caller
    return ()
end

#
# Getters
#

@view
func get_public_key{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (res) = public_key.read()
    return (res=res)
end

@view
func get_nonce{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (res : felt):
    let (res) = current_nonce.read()
    return (res=res)
end

# @notice Check if the transaction signature is valid
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
        let (caller) = get_caller_address()
        let (registry) = registry_address.read()
        let (version) = contract_version.read()

        # To-Do Verify whether call came from node operator

        let (_public_key) = IAccount.get_public_key(contract_address=liquidator_address_)
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

@view
func get_trading_volume{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (res) = trading_volume.read()
    return (res=res)
end

@view
func get_balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt
) -> (res : felt):
    let (res) = balance.read(assetID=assetID_)
    return (res=res)
end

@view
func get_order_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    orderID_ : felt
) -> (res : OrderDetails):
    let (res) = order_mapping.read(orderID=orderID_)
    return (res=res)
end

# @notice get L1 address of the user
@view
func get_L1_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (res) = L1_address.read()
    return (res=res)
end

@view
func get_amount_to_be_sold{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    order_id_ : felt
) -> (res : felt):
    let (res) = amount_to_be_sold.read(order_id=order_id_)
    return (res=res)
end

@view
func get_deleveraged_or_liquidatable_position{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr
}() -> (order_id : felt, amount_to_be_sold : felt):
    alloc_locals
    let (order_id_) = deleveraged_or_liquidatable_position.read()
    let (order_details) = get_order_data(order_id_)
    local amount_to_be_sold_
    if order_details.status == 5:
        let (amount) = amount_to_be_sold.read(order_id=order_id_)
        assert amount_to_be_sold_ = amount
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        assert amount_to_be_sold_ = 0
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end
    return (order_id=order_id_, amount_to_be_sold=amount_to_be_sold_)
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
    alloc_locals
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

    if pos_details.status == 4:
        return populate_array_positions(iterator + 1, array_list_len, array_list)
    else:
        if pos_details.status == 7:
            return populate_array_positions(iterator + 1, array_list_len, array_list)
        else:
            assert array_list[array_list_len] = order_details_w_id
            return populate_array_positions(iterator + 1, array_list_len + 1, array_list)
        end
    end
end

# @notice Function to get all the open positions
# @return array_list_len - Length of the array_list
# @return array_list - Fully populated list of OrderDetails
@view
func return_array_positions{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (array_list_len : felt, array_list : OrderDetailsWithIDs*):
    alloc_locals

    let (array_list : OrderDetailsWithIDs*) = alloc()
    return populate_array_positions(iterator=0, array_list_len=0, array_list=array_list)
end

# @notice Internal Function called by return_array_collaterals to recursively add collateralBalance to the array and return it
# @param array_list_len_ - Stores the current length of the populated array
# @param array_list_ - Array of CollateralBalance filled up to the index
# @return array_list_len - Length of the array_list
# @return array_list - Fully populated list of CollateralBalance
func populate_array_collaterals{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    array_list_len_ : felt, array_list_ : CollateralBalance*
) -> (array_list_len : felt, array_list : CollateralBalance*):
    alloc_locals
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

# @notice Function to get all use collaterals
# @return array_list_len - Length of the array_list
# @return array_list - Fully populated list of CollateralBalance
@view
func return_array_collaterals{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (array_list_len : felt, array_list : CollateralBalance*):
    alloc_locals

    let (array_list : CollateralBalance*) = alloc()
    return populate_array_collaterals(0, array_list)
end

# @notice Internal Function called by get_withdrawal_history to recursively add WithdrawalRequest to the array and return it
# @param withdrawal_list_len_ - Stores the current length of the populated withdrawals array
# @param withdrawal_list_ - Array of WithdrawalRequest filled up to the index
# @return withdrawal_list_len - Length of the withdrawal_list
# @return withdrawal_list - Fully populated list of Withdrawals
func populate_withdrawals_array{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    withdrawal_list_len_ : felt, withdrawal_list_ : WithdrawalHistory*
) -> (withdrawal_list_len : felt, withdrawal_list : WithdrawalHistory*):
    alloc_locals
    let (withdrawal_history) = withdrawal_history_array.read(index=withdrawal_list_len_)

    if withdrawal_history.collateral_id == 0:
        return (withdrawal_list_len_, withdrawal_list_)
    end

    assert withdrawal_list_[withdrawal_list_len_] = withdrawal_history
    return populate_withdrawals_array(withdrawal_list_len_ + 1, withdrawal_list_)
end

# @notice Function to get withdrawal history
# @return withdrawal_list_len - Length of the withdrawal list
# @return withdrawal_list - Fully populated list of withdrawals
@view
func get_withdrawal_history{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (withdrawal_list_len : felt, withdrawal_list : WithdrawalHistory*):
    alloc_locals

    let (withdrawal_list : WithdrawalHistory*) = alloc()
    return populate_withdrawals_array(0, withdrawal_list)
end

#
# Setters
#

@external
func set_public_key{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    new_public_key : felt
):
    assert_only_self()
    public_key.write(new_public_key)
    return ()
end

#
# Business logic
#

# @notice External function called by the Trading Contract
# @param amount - Amount of funds to transfer from this contract
@external
func transfer_from{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount : felt
) -> ():
    alloc_locals

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
    return ()
end

@view
func timestamp_check{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id : felt
) -> (is_eight_hours : felt):
    alloc_locals
    # Get the latest block
    let (block_timestamp) = get_block_timestamp()

    # Fetch the last updated time
    let (last_call) = last_updated.read(market_id=market_id)

    # Minimum time before the second call
    let min_time = last_call + 28000
    let (is_eight_hours) = is_le(block_timestamp, min_time)

    return (is_eight_hours)
end

# @notice External function called by the ABR Payment contract
# @param assetID_ - asset ID of the collateral that needs to be transferred
# @param amount - Amount of funds to transfer from this contract
@external
func transfer_from_abr{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, marketID_ : felt, amount : felt
):
    alloc_locals

    # Check if the caller is trading contract
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (abr_payment_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=19, version=version
    )

    with_attr error_message("Caller is not authorized to do transferFrom in account contract."):
        assert caller = abr_payment_address
    end

    # Reduce the amount from balance
    let (balance_) = balance.read(assetID=assetID_)
    balance.write(assetID=assetID_, value=balance_ - amount)

    # Update the timestamp of last called
    let (block_timestamp) = get_block_timestamp()
    last_updated.write(market_id=marketID_, value=block_timestamp)
    return ()
end

# @notice External function called by the ABR Payment contract
# @param assetID_ - asset ID of the collateral that needs to be transferred
# @param amount - Amount of funds to transfer to this contract
@external
func transfer_abr{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, marketID_ : felt, amount : felt
):
    alloc_locals

    # Check if the caller is trading contract
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (abr_payment_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=19, version=version
    )
    with_attr error_message("Caller is not authorized to do transfer in account contract."):
        assert caller = abr_payment_address
    end

    # Add amount to balance
    let (balance_) = balance.read(assetID=assetID_)
    balance.write(assetID=assetID_, value=balance_ + amount)

    # Update the timestamp of last called
    let (block_timestamp) = get_block_timestamp()
    last_updated.write(market_id=marketID_, value=block_timestamp)

    return ()
end

# @notice External function called by the Trading Contract to transfer funds from account contract
# @param assetID_ - asset ID of the collateral that needs to be transferred
# @param amount - Amount of funds to transfer to this contract
@external
func transfer{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount : felt
) -> ():
    alloc_locals

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
    return ()
end

# @notice Function to execute transactions signed by this account
# @param to - Contract address to which to send the transaction
# @param selector - Function selector of the function to call
# @param calldata_len - Length of the paramaters to be passed to the function
# @param calldata - Array of parameters
# @param nonce - (Currently not used)
# @return response_len - Length of the return values from the function
# @return response - Array of return values
@external
func execute{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(to : felt, selector : felt, calldata_len : felt, calldata : felt*, nonce : felt) -> (
    response_len : felt, response : felt*
):
    alloc_locals

    let (__fp__, _) = get_fp_and_pc()
    let (_address) = get_contract_address()
    let (_current_nonce) = current_nonce.read()

    local message : Message = Message(
        _address,
        to,
        selector,
        calldata,
        calldata_size=calldata_len,
        _current_nonce
        )

    # validate transaction
    let (hash) = hash_message(&message)
    let (signature_len, signature) = get_tx_signature()
    is_valid_signature(hash, signature_len, signature)

    # bump nonce
    current_nonce.write(_current_nonce + 1)

    # execute call
    let response = call_contract(
        contract_address=message.to,
        function_selector=message.selector,
        calldata_size=message.calldata_size,
        calldata=message.calldata,
    )

    return (response_len=response.retdata_size, response=response.retdata)
end

# @notice Function to hash the transaction parameters
# @param message - Struct of details to hash
# @param res - Hash of the parameters
func hash_message{pedersen_ptr : HashBuiltin*}(message : Message*) -> (res : felt):
    alloc_locals
    # we need to make `res_calldata` local
    # to prevent the reference from being revoked
    let (local res_calldata) = hash_calldata(message.calldata, message.calldata_size)
    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (hash_state_ptr) = hash_init()
        # first three iterations are 'sender', 'to', and 'selector'
        let (hash_state_ptr) = hash_update(hash_state_ptr, message, 3)
        let (hash_state_ptr) = hash_update_single(hash_state_ptr, res_calldata)
        let (hash_state_ptr) = hash_update_single(hash_state_ptr, message.nonce)
        let (res) = hash_finalize(hash_state_ptr)
        let pedersen_ptr = hash_ptr
        return (res=res)
    end
end

# @notice Function to hash the calldata
# @param calldata - Array of params
# @param calldata_size - Length of the params
# @return res - hash of the calldata
func hash_calldata{pedersen_ptr : HashBuiltin*}(calldata : felt*, calldata_size : felt) -> (
    res : felt
):
    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (hash_state_ptr) = hash_init()
        let (hash_state_ptr) = hash_update(hash_state_ptr, calldata, calldata_size)
        let (res) = hash_finalize(hash_state_ptr)
        let pedersen_ptr = hash_ptr
        return (res=res)
    end
end

# #### TODO: Remove; Only for testing purposes #####
@external
func set_balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount_ : felt
):
    let (curr_balance) = get_balance(assetID_)
    balance.write(assetID=assetID_, value=amount_)
    let (array_len) = collateral_array_len.read()

    tempvar syscall_ptr = syscall_ptr
    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
    tempvar range_check_ptr = range_check_ptr
    if curr_balance == 0:
        add_collateral(new_asset_id=assetID_, iterator=0, length=array_len)
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    return ()
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
        assert posDetails.status = 4
    end

    let (arr_len) = position_array_len.read()
    let (last_id) = position_array.read(index=arr_len - 1)

    position_array.write(index=id_, value=last_id)
    position_array.write(index=arr_len - 1, value=0)

    position_array_len.write(arr_len - 1)
    return (1)
end

# @notice Function to hash the order parameters
# @param message - Struct of order details to hash
# @param res - Hash of the details
func hash_order{pedersen_ptr : HashBuiltin*}(orderRequest : OrderRequest*) -> (res : felt):
    alloc_locals

    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (hash_state_ptr) = hash_init()
        let (hash_state_ptr) = hash_update(hash_state_ptr, orderRequest, 10)
        let (res) = hash_finalize(hash_state_ptr)
        let pedersen_ptr = hash_ptr
        return (res=res)
    end
end

# @notice Function to hash the withdrawal request parameters
# @param message - Struct of order details to hash
# @param res - Hash of the details
func hash_withdrawal_request{pedersen_ptr : HashBuiltin*}(
    withdrawal_request_ : WithdrawalHistory*
) -> (res : felt):
    alloc_locals

    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (hash_state_ptr) = hash_init()
        let (hash_state_ptr) = hash_update(hash_state_ptr, withdrawal_request_, 2)
        let (res) = hash_finalize(hash_state_ptr)
        let pedersen_ptr = hash_ptr
        return (res=res)
    end
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
            # status_ == 1, partially opened
            # status_ == 2, fully opened
            if request.positionSize == size:
                assert status_ = 2
            else:
                assert status_ = 1
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
            if orderDetails.status == 5:
                tempvar range_check_ptr = range_check_ptr
            else:
                assert_le(orderDetails.status, 3)
                tempvar range_check_ptr = range_check_ptr
            end

            # Check if the order is fully filled by executing the current one
            if request.positionSize == size + orderDetails.portionExecuted:
                status_ = 2
            else:
                status_ = 1
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
        assert_not_equal(request.direction, orderDetails.direction)

        # Assert that the order exists
        assert_not_zero(orderDetails.positionSize)
        assert_nn(orderDetails.portionExecuted - size)

        local new_leverage
        if request.orderType == 4:
            let total_value = margin_amount + borrowed_amount
            let (leverage_) = Math64x61_div(total_value, margin_amount)
            new_leverage = leverage_
        else:
            new_leverage = request.leverage
        end
        tempvar range_check_ptr = range_check_ptr

        # Check if the order is fully closed or not
        # status_ == 4, fully closed
        # status_ == 3, partially closed
        # status_ == 5, toBeDeleveraged
        # status_ == 6, toBeLiquidated
        # status_ == 7, fullyLiquidated
        if orderDetails.portionExecuted - size == 0:
            if request.orderType == 3:
                assert status_ = 7
            else:
                assert status_ = 4
            end
        else:
            if request.orderType == 4:
                assert status_ = 5
            else:
                if request.orderType == 3:
                    assert status_ = 6
                else:
                    assert status_ = 3
                end
            end
        end

        # Update the amount to be sold after deleveraging
        if orderDetails.status == 5:
            let (amount) = amount_to_be_sold.read(order_id=request.parentOrder)
            let updated_amount = amount - size
            let (positive_updated_amount) = abs_value(updated_amount)
            # to64x61(0.0000000001) = 230584300. We are comparing result with this number to fix overflow issues
            let (result) = is_le(updated_amount, 230584300)
            local amount_to_be_updated
            if result == 1:
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

# @notice Internal function to recursively find the index of the withdrawal history to be updated
# @param collateral_id_ - Id of the collateral on which user submitted withdrawal request
# @param amount_ - Amount of funds that user has withdrawn
# @param timestamp_ - Time at which user submitted withdrawal request
# @param arr_len_ - current index which is being checked to be updated
# @return index - returns the index which needs to be updated
func find_index_to_be_updated_recurse{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr
}(collateral_id_ : felt, amount_ : felt, timestamp_ : felt, arr_len_ : felt) -> (index : felt):
    alloc_locals

    if arr_len_ == 0:
        return (-1)
    end

    let (request : WithdrawalHistory) = withdrawal_history_array.read(index=arr_len_ - 1)

    local first_check_counter
    local second_check_counter
    local third_check_counter
    if request.collateral_id == collateral_id_:
        first_check_counter = 1
    end
    if request.amount == amount_:
        second_check_counter = 1
    end
    if request.timestamp == timestamp_:
        third_check_counter = 1
    end

    let counter = first_check_counter + second_check_counter + third_check_counter
    if counter == 3:
        return (arr_len_ - 1)
    end
    return find_index_to_be_updated_recurse(collateral_id_, amount_, timestamp_, arr_len_ - 1)
end

# @notice function to update l1 fee and node operators l1 wallet address
# @param collateral_id_ - Id of the collateral on which user submitted withdrawal request
# @param amount_ - Amount of funds that user has withdrawn
# @param timestamp_ - Time at which user submitted withdrawal request
# @param node_operator_L1_address_ - Node operators L1 address
# @param L1_fee_amount_ - Gas fee in L1
# @param L1_fee_collateral_id_ - Collateral used to pay L1 gas fee
@external
func update_withdrawal_history{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(
    collateral_id_ : felt,
    amount_ : felt,
    timestamp_ : felt,
    node_operator_L1_address_ : felt,
    L1_fee_amount_ : felt,
    L1_fee_collateral_id_ : felt,
):
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
    let (index) = find_index_to_be_updated_recurse(collateral_id_, amount_, timestamp_, arr_len)
    if index != -1:
        let (history) = withdrawal_history_array.read(index=index)
        let updated_history = WithdrawalHistory(
            collateral_id=collateral_id_,
            amount=amount_,
            timestamp=timestamp_,
            node_operator_L1_address=node_operator_L1_address_,
            node_operator_L2_address=history.node_operator_L2_address,
            L1_fee_amount=L1_fee_amount_,
            L1_fee_collateral_id=L1_fee_collateral_id_,
            L2_fee_amount=history.L2_fee_amount,
            L2_fee_collateral_id=history.L2_fee_collateral_id,
        )
        withdrawal_history_array.write(index=index, value=updated_history)
        return ()
    end
    return ()
end

# @notice Function to withdraw funds
# @param collateral_id_ - Id of the collateral on which user submitted withdrawal request
# @param amount_ - Amount of funds that user wants to withdraw
# @param sig_r_ - R part of signature
# @param sig_s_ - S part of signature
# @param node_operator_L2_address_ - Node operators L2 address
# @param L1_fee_amount_ - Gas fee in L1
# @param L1_fee_collateral_id_ - Collateral used to pay L1 gas fee
# @param L2_fee_amount_ - Gas fee in L2
# @param L2_fee_collateral_id_ - Collateral used to pay L2 gas fee
@external
func withdrawal{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(
    collateral_id_ : felt,
    amount_ : felt,
    sig_r_ : felt,
    sig_s_ : felt,
    node_operator_L2_address_ : felt,
    L1_fee_amount_ : felt,
    L1_fee_collateral_id_ : felt,
    L2_fee_amount_ : felt,
    L2_fee_collateral_id_ : felt,
):
    alloc_locals
    let (__fp__, _) = get_fp_and_pc()

    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (signature_ : felt*) = alloc()
    assert signature_[0] = sig_r_
    assert signature_[1] = sig_s_

    # Calculate the timestamp
    let (timestamp_) = get_block_timestamp()

    # Create a withdrawal history object
    local withdrawal_history_ : WithdrawalHistory = WithdrawalHistory(
        collateral_id=collateral_id_,
        amount=amount_,
        timestamp=timestamp_,
        node_operator_L1_address=0,
        node_operator_L2_address=node_operator_L2_address_,
        L1_fee_amount=L1_fee_amount_,
        L1_fee_collateral_id=L1_fee_collateral_id_,
        L2_fee_amount=L2_fee_amount_,
        L2_fee_collateral_id=L2_fee_collateral_id_
        )

    # hash the parameters
    let (hash) = hash_withdrawal_request(&withdrawal_history_)

    # check if Tx is signed by the user
    is_valid_signature(hash, 2, signature_)

    # Make sure 'amount' is positive.
    assert_nn(amount_)

    # Compute current L1 fee collateral balance
    let (L1_fee_collateral_balance) = balance.read(assetID=L1_fee_collateral_id_)
    with_attr error_message("L1 fee collateral balance should be more than L1 fee"):
        assert_le(L1_fee_amount_, L1_fee_collateral_balance)
    end
    tempvar new_L1_fee_collateral_balance = L1_fee_collateral_balance - L1_fee_amount_

    # Update L1 fee collateral balance
    balance.write(assetID=L1_fee_collateral_id_, value=new_L1_fee_collateral_balance)

    # Compute current L2 fee collateral balance
    let (L2_fee_collateral_balance) = balance.read(assetID=L2_fee_collateral_id_)
    with_attr error_message("L2 fee collateral balance should be more than L2 fee"):
        assert_le(L2_fee_amount_, L2_fee_collateral_balance)
    end
    tempvar new_L2_fee_collateral_balance = L2_fee_collateral_balance - L2_fee_amount_

    # Update L2 fee collateral balance
    balance.write(assetID=L2_fee_collateral_id_, value=new_L2_fee_collateral_balance)

    # Compute current balance
    let (current_balance) = balance.read(assetID=collateral_id_)
    with_attr error_message("Withdrawal amount requested should be less than balance"):
        assert_le(amount_, current_balance)
    end
    tempvar new_balance = current_balance - amount_

    # Update the new balance
    balance.write(assetID=collateral_id_, value=new_balance)

    # get L2 Account contract address
    let (user_l2_address) = get_contract_address()

    # Update the fees to be paid by user in withdrawal fee balance contract
    let (withdrawal_fee_balance_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=WithdrawalFeeBalance_INDEX, version=version
    )
    IWithdrawalFeeBalance.update_withdrawal_fee_mapping(
        contract_address=withdrawal_fee_balance_address,
        user_l2_address_=user_l2_address,
        collateral_id_=collateral_id_,
        fee_to_add_=L2_fee_amount_,
    )

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get asset contract address
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    )
    # Reading token decimal field of an asset
    let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=collateral_id_)
    tempvar decimal = asset.token_decimal

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
        user_l1_address_=user_l1_address,
        collateral_id_=collateral_id_,
        amount_=amount_,
        timestamp_=timestamp_,
    )

    # Update Withdrawal history
    let (array_len) = withdrawal_history_array_len.read()
    withdrawal_history_array.write(index=array_len, value=withdrawal_history_)
    withdrawal_history_array_len.write(array_len + 1)

    # Get L1 ZKX contract address
    let (L1_ZKX_contract_address) = L1_ZKX_address.read()

    # Send the withdrawal message.
    let (message_payload : felt*) = alloc()
    assert message_payload[0] = MESSAGE_WITHDRAW
    assert message_payload[1] = user_l1_address
    assert message_payload[2] = collateral_id_
    assert message_payload[3] = amount_in_felt
    assert message_payload[4] = timestamp_

    # Send Message to L1
    send_message_to_l1(to_address=L1_ZKX_contract_address, payload_size=5, payload=message_payload)

    return ()
end

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
    # Make sure the message was sent by the intended L1 contract.
    let (L1_ZKX_contract_address) = L1_ZKX_address.read()
    assert from_address = L1_ZKX_contract_address

    # Update the L1 address
    L1_address.write(user)

    # Reading token decimal field of an asset
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get asset contract address
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    )
    let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=assetID_)
    tempvar decimal = asset.token_decimal

    let (ten_power_decimal) = pow(10, decimal)
    let (decimal_in_64x61_format) = Math64x61_fromFelt(ten_power_decimal)

    let (amount_in_64x61_format) = Math64x61_fromFelt(amount)
    let (amount_in_decimal_representation) = Math64x61_div(
        amount_in_64x61_format, decimal_in_64x61_format
    )

    # Read the current balance.
    let (res) = balance.read(assetID=assetID_)

    # Compute and update the new balance.
    tempvar new_balance = res + amount_in_decimal_representation
    balance.write(assetID=assetID_, value=new_balance)

    let (array_len) = collateral_array_len.read()
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

    return ()
end

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
    with_attr error_message("Amount to be sold should be less than portion executed"):
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
        status_ = 6
    else:
        status_ = 5
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

    return ()
end
