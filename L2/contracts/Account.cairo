%lang starknet
%builtins pedersen range_check ecdsa bitwise

from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.messages import send_message_to_l1
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.bitwise import bitwise_or
from starkware.starknet.common.syscalls import get_contract_address
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
from starkware.cairo.common.math import assert_le, assert_not_equal, assert_not_zero, assert_nn
from starkware.cairo.common.pow import pow

from contracts.Math_64x61 import mul_fp, div_fp, to64x61, from64x61

const L1_CONTRACT_ADDRESS = (0x88d2EE8A225D281cAa435F532F51c9844F05a4d9)
const MESSAGE_WITHDRAW = 0

#
# Structs
#

# Struct to pass the transactions to the contract
struct Message:
    member sender : felt
    member to : felt
    member selector : felt
    member calldata : felt*
    member calldata_size : felt
    member nonce : felt
end

# Struct to pass the order to this contract
struct OrderRequest:
    member orderID : felt
    member assetID : felt
    member collateralID : felt
    member price : felt
    member orderType : felt
    member positionSize : felt
    member direction : felt
    member closeOrder : felt
    member leverage : felt
    member isLiquidation : felt
    member liquidatorAddress : felt
    member parentOrder : felt
end

# Struct to pass signatures to this contract
struct Signature:
    member r_value : felt
    member s_value : felt
end

# status 0: initialized
# status 1: partial
# status 2: executed
# status 3: close partial
# status 4: close
# status 5: toBeLiquidated
# status 6: fullyLiquidated
struct OrderDetails:
    member assetID : felt
    member collateralID : felt
    member price : felt
    member executionPrice : felt
    member positionSize : felt
    member orderType : felt
    member direction : felt
    member portionExecuted : felt
    member status : felt
    member marginAmount : felt
    member borrowedAmount : felt
end

# status 0: initialized
# status 1: partial
# status 2: executed
# status 3: close partial
# status 4: close
struct OrderDetailsWithIDs:
    member orderID : felt
    member assetID : felt
    member collateralID : felt
    member price : felt
    member executionPrice : felt
    member positionSize : felt
    member orderType : felt
    member direction : felt
    member portionExecuted : felt
    member status : felt
    member marginAmount : felt
    member borrowedAmount : felt
end

# @notice struct to store details of assets
struct Asset:
    member ticker : felt
    member short_name : felt
    member tradable : felt
    member collateral : felt
    member token_decimal : felt
    member metadata_id : felt
    member tick_size : felt
    member step_size : felt
    member minimum_order_size : felt
    member minimum_leverage : felt
    member maximum_leverage : felt
    member currently_allowed_leverage : felt
    member maintenance_margin_fraction : felt
    member initial_margin_fraction : felt
    member incremental_initial_margin_fraction : felt
    member incremental_position_size : felt
    member baseline_position_size : felt
    member maximum_position_size : felt
end

struct CollateralBalance:
    member assetID : felt
    member balance : felt
end

#
# Storage
#

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of AdminAuth contract
@storage_var
func registry_address() -> (contract_address : felt):
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

# L1 User associated with the account
@storage_var
func L1_address() -> (res : felt):
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
# Constructor
#

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    public_key_ : felt, registry_address_ : felt, version_ : felt
):
    public_key.write(public_key_)
    registry_address.write(value=registry_address_)
    contract_version.write(value=version_)
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
        contract_address=registry, index=5, version=version
    )

    with_attr error_message("Caller is not authorized to do transferFrom in account contract."):
        assert caller = trading_address
    end

    balance.write(assetID=assetID_, value=balance_ - amount)
    return ()
end

# @notice External function called by the Trading Contract
# @param amount - Amount of funds to transfer to this contract
@external
func transfer{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount : felt
) -> ():
    alloc_locals

    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr

    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=5, version=version
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

# TODO: Remove; Only for testing purposes
@external
func set_balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount : felt
):
    let (curr_balance) = get_balance(assetID_)
    balance.write(assetID=assetID_, value=curr_balance + amount)
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
# @returns 1 - If successfully added
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
# @returns 1 - If successfully removed
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

# @notice Internal Function called by return array to recursively add positions to the array and return it
# @param iterator - Index of the position_array currently pointing to
# @param array_list_len - Stores the current length of the populated array
# @param array_list - Array of OrderRequests filled up to the index
# @returns array_list_len - Length of the array_list
# @returns array_list - Fully populated list of OrderDetails
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

    let (is_valid_state) = is_le(pos_details.status, 3)

    if is_valid_state == 1:
        assert array_list[array_list_len] = order_details_w_id
        return populate_array_positions(iterator + 1, array_list_len + 1, array_list)
    else:
        return populate_array_positions(iterator + 1, array_list_len, array_list)
    end
end

# @notice Function to get all the open positions
# @returns array_list_len - Length of the array_list
# @returns array_list - Fully populated list of OrderDetails
@view
func return_array_positions{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (array_list_len : felt, array_list : OrderDetailsWithIDs*):
    alloc_locals

    let (array_list : OrderDetailsWithIDs*) = alloc()
    return populate_array_positions(iterator=0, array_list_len=0, array_list=array_list)
end

# @notice Internal Function called by return_array_collaterals to recursively add collateralBalance to the array and return it
# @param iterator - Index of the position_array currently pointing to
# @param array_list_len - Stores the current length of the populated array
# @param array_list - Array of CollateralBalance filled up to the index
# @returns array_list_len - Length of the array_list
# @returns array_list - Fully populated list of CollateralBalance
func populate_array_collaterals{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    array_list_len : felt, array_list : CollateralBalance*
) -> (array_list_len : felt, array_list : CollateralBalance*):
    alloc_locals
    let (collateral_id) = collateral_array.read(index=array_list_len)

    if collateral_id == 0:
        return (array_list_len, array_list)
    end

    let (collateral_balance : felt) = balance.read(assetID=collateral_id)
    let collateral_balance_struct = CollateralBalance(
        assetID=collateral_id, balance=collateral_balance
    )

    assert array_list[array_list_len] = collateral_balance_struct
    return populate_array_collaterals(array_list_len + 1, array_list)
end

# @notice Function to get all use collaterals
# @returns array_list_len - Length of the array_list
# @returns array_list - Fully populated list of CollateralBalance
@view
func return_array_collaterals{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (array_list_len : felt, array_list : CollateralBalance*):
    alloc_locals

    let (array_list : CollateralBalance*) = alloc()
    return populate_array_collaterals(array_list_len=0, array_list=array_list)
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

# @notice Function called by Trading Contract
# @param request - Details of the order to be executed
# @param signature - Details of the signature
# @param size - Size of the Order to be executed
# @param execution_price - Price at which the order should be executed
# @param amount - TODO: Amount of funds that user must send/receive
# @returns 1, if executed correctly
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
        contract_address=registry, index=5, version=version
    )
    with_attr error_message(
            "Trading contract is not authorized to execute order in account contract."):
        assert caller = trading_address
    end

    # hash the parameters
    let (hash) = hash_order(&request)

    # check if signed by the user/liquidator
    is_valid_signature_order(hash, signature, request.isLiquidation, request.liquidatorAddress)

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
            let (size_by_leverage) = div_fp(size, request.leverage)
            with_attr error_message(
                    "Paritally executed + remaining should be less than position in account contract."):
                assert_le(size + orderDetails.portionExecuted, request.positionSize)
            end

            # Check if the order is in the process of being closed
            assert_le(orderDetails.status, 3)

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
                executionPrice=orderDetails.executionPrice,
                positionSize=orderDetails.positionSize,
                orderType=request.orderType,
                direction=orderDetails.direction,
                portionExecuted=orderDetails.portionExecuted + size,
                status=status_,
                marginAmount=margin_amount,
                borrowedAmount=borrowed_amount,
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

        # Check if the order is fully closed or not
        # status_ == 4, fully closed
        # status_ == 3, partially closed
        if orderDetails.portionExecuted - size == 0:
            if request.isLiquidation == 1:
                assert status_ = 6
            else:
                assert status_ = 4
            end
        else:
            if request.isLiquidation == 1:
                assert status_ = 5
            else:
                assert status_ = 3
            end
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

# @notice view function which checks the signature passed is valid
# @param hash - Hash of the order to check against
# @param signature - Signature passed to the contract to check against
# @returns reverts, if there is an error
@view
func is_valid_signature_order{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(hash : felt, signature : Signature, is_liquidator, liquidator_address_ : felt) -> ():
    alloc_locals

    let sig_r = signature.r_value
    let sig_s = signature.s_value
    local pub_key

    if is_liquidator == 1:
        let (caller) = get_caller_address()
        let (registry) = registry_address.read()
        let (version) = contract_version.read()

        # Get liquidator's contract address
        let (liquidator_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=13, version=version
        )

        with_attr error_message("The signer is not a authorized liquidator"):
            assert liquidator_address = liquidator_address_
        end

        let (_public_key) = IAccount.get_public_key(contract_address=liquidator_address)
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

# @notice Function to withdraw funds
# @param amount - The Amount of funds that user wants to withdraw
@external
func withdraw{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount : felt
):
    alloc_locals
    # Make sure 'amount' is positive.
    assert_nn(amount)

    let (res) = balance.read(assetID=assetID_)
    tempvar new_balance = res - amount

    # Make sure the new balance will be positive.
    assert_nn(new_balance)

    # Update the new balance.
    balance.write(assetID=assetID_, value=new_balance)

    # Reading token decimal field of an asset
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get asset contract address
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=1, version=version
    )
    let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=assetID_)
    tempvar decimal = asset.token_decimal

    let (ten_power_decimal) = pow(10, decimal)
    let (decimal_in_64x61_format) = to64x61(ten_power_decimal)

    let (amount_times_ten_power_decimal) = mul_fp(amount, decimal_in_64x61_format)
    let (amount_in_felt) = from64x61(amount_times_ten_power_decimal)

    # Get the L1 Metamask address
    let (L2_account_address) = get_contract_address()
    let (user) = L1_address.read()

    # Send the withdrawal message.
    let (message_payload : felt*) = alloc()
    assert message_payload[0] = MESSAGE_WITHDRAW
    assert message_payload[1] = user
    assert message_payload[2] = amount_in_felt
    assert message_payload[3] = assetID_
    send_message_to_l1(to_address=L1_CONTRACT_ADDRESS, payload_size=4, payload=message_payload)

    return ()
end

# @notice Function to handle deposit from L1ZKX contract
# @param from_address - The address from where deposit function is called from
# @param user - User's Metamask account address
# @param amount - The Amount of funds that user wants to withdraw
@l1_handler
func deposit{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    from_address : felt, user : felt, amount : felt, assetID_ : felt
):
    alloc_locals
    # Make sure the message was sent by the intended L1 contract.
    assert from_address = L1_CONTRACT_ADDRESS

    # Update the L1 address
    L1_address.write(user)

    # Reading token decimal field of an asset
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get asset contract address
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=1, version=version
    )
    let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=assetID_)
    tempvar decimal = asset.token_decimal

    let (ten_power_decimal) = pow(10, decimal)
    let (decimal_in_64x61_format) = to64x61(ten_power_decimal)

    let (amount_in_64x61_format) = to64x61(amount)
    let (amount_in_decimal_representation) = div_fp(amount_in_64x61_format, decimal_in_64x61_format)

    # Read the current balance.
    let (res) = balance.read(assetID=assetID_)

    # Compute and update the new balance.
    tempvar new_balance = res + amount_in_decimal_representation
    balance.write(assetID=assetID_, value=new_balance)

    let (array_len) = collateral_array_len.read()
    let (balance_collateral) = balance.read(assetID=assetID_)

    tempvar syscall_ptr = syscall_ptr
    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
    tempvar range_check_ptr = range_check_ptr
    if balance_collateral == 0:
        add_collateral(new_asset_id=assetID_, iterator=0, length=array_len)
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

# @notice Function called by liquidate contract to mark the position as liquidated
# @param id - Order Id of the position to be marked
@external
func liquidate_position{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt
):
    alloc_locals

    let (orderDetails : OrderDetails) = order_mapping.read(orderID=id)

    # Check if the caller is the liquidator contract
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (liquidate_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=11, version=version
    )

    with_attr error_message("Only liquidate contract is allowed to call for liquidation"):
        assert caller = liquidate_address
    end

    # Create a new struct with the updated details
    let updated_order = OrderDetails(
        assetID=orderDetails.assetID,
        collateralID=orderDetails.collateralID,
        price=orderDetails.price,
        executionPrice=orderDetails.executionPrice,
        positionSize=orderDetails.positionSize,
        orderType=orderDetails.orderType,
        direction=orderDetails.direction,
        portionExecuted=orderDetails.portionExecuted,
        status=5,
        marginAmount=orderDetails.marginAmount,
        borrowedAmount=orderDetails.borrowedAmount,
    )

    # Write to the mapping
    order_mapping.write(orderID=id, value=updated_order)

    return ()
end

# @notice AuthorizedRegistry interface
@contract_interface
namespace IAuthorizedRegistry:
    func get_contract_address(index : felt, version : felt) -> (address : felt):
    end
end

# @notice Asset interface
@contract_interface
namespace IAsset:
    func getAsset(id : felt) -> (currAsset : Asset):
    end
end

# @notice Account interface
@contract_interface
namespace IAccount:
    func get_public_key() -> (res : felt):
    end
end
