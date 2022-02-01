%lang starknet
%builtins pedersen range_check ecdsa

from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.common.syscalls import get_contract_address
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.starknet.common.syscalls import call_contract, get_caller_address, get_tx_signature
from starkware.cairo.common.hash_state import (hash_init, hash_finalize, hash_update, hash_update_single)
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.math import assert_le, assert_not_equal, assert_not_zero, assert_nn

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
    member ticker : felt
    member price : felt
    member orderType : felt
    member positionSize : felt
    member direction : felt
    member closeOrder : felt
    member parentOrder : felt
end

# Struct to pass signatures to this contract
struct Signature:
    member r_value: felt
    member s_value: felt
end

# status 0: initialized
# status 1: partial
# status 2: executed
# status 3: close partial
# status 4: close
struct OrderDetails:
    member ticker: felt
    member price: felt
    member executionPrice: felt
    member positionSize: felt
    member orderType: felt
    member direction: felt
    member portionExecuted: felt
    member status: felt
end
#
# Storage
#

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
func balance() -> (res : felt):
end

@storage_var
func authorized_registry() -> (res : felt):
end

@storage_var
func allowance(address: felt) -> (res : felt):
end

@storage_var
func locked_balance() -> (res : felt):
end

@storage_var
func order_mapping(orderID: felt) -> (res : OrderDetails):
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
        res : felt):
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
        res : felt):
    let (res) = trading_volume.read()
    return (res=res)
end

@view
func get_balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        res : felt):
    let (res) = balance.read()
    return (res=res)
end

@view
func get_locked_balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        res : felt):
    let (res) = locked_balance.read()
    return (res=res)
end

@view
func get_order_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    order_ID : felt
) -> (
    res : OrderDetails
):
    let (res) = order_mapping.read(orderID=order_ID)
    return (res=res)
end


@view
func get_allowance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address_ : felt
) -> (
    res : felt
):
    let (res) = allowance.read(address = address_)
    return (res=res)
end

#
# Setters
#

@external
func set_public_key{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        new_public_key : felt):
    assert_only_self()
    public_key.write(new_public_key)
    return ()
end

#
# Constructor
#

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        _public_key : felt, _registry : felt):
    public_key.write(_public_key)
    authorized_registry.write(_registry)
    return ()
end

#
# Business logic
#

# @notice Approve funds to be transfered by Trading Contract
# @param address - Address to approve funds to
# @param allowance_ - Amount of funds to approve
@external
func approve{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(  
    address_ : felt,
    allowance_ : felt
) -> ():
    alloc_locals
    assert_only_self()

    let (authorized_registry_) = authorized_registry.read()
    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 

    let (is_trading_contract) = IAuthorizedRegistry.get_registry_value(contract_address = authorized_registry_, address = address_, action = 3)
    assert is_trading_contract = 1

    allowance.write(address = address_, value=allowance_)

    return ()
end


# @notice External function called by the Trading Contractg
# @param amount - Amount of funds to transfer from this contract
@external
func transfer_from{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr,
}(
    amount : felt
) -> ():

    let (caller) = get_caller_address()
    let (allowance_) = allowance.read(address = caller)
    let (balance_) = balance.read()

    assert_le(amount, allowance_)
    assert_nn(balance_ - amount)
    allowance.write(address = caller, value = allowance_ - amount)
    balance.write(balance_ - amount)
    return ()
end


# @notice External function called by the Trading Contractg
# @param amount - Amount of funds to transfer from this contract
@external
func transfer{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr,
}(
    amount : felt
) -> ():
    alloc_locals

    let (caller) = get_caller_address()
    let (authorized_registry_) = authorized_registry.read()
    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 

    let (is_trading_contract) = IAuthorizedRegistry.get_registry_value(contract_address = authorized_registry_, address = caller, action = 3)
    assert is_trading_contract = 1

    assert_nn(amount)
    let (balance_) = balance.read()
    balance.write(balance_ + amount)
    return ()
end

# @notice Check if the transaction signature is valid
# @param hash - Hash of the transaction parameters
# @param singature_len - Length of the signatures
# @param signature - Array of signatures
@view
func is_valid_signature{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr,
        ecdsa_ptr : SignatureBuiltin*}(hash : felt, signature_len : felt, signature : felt*) -> ():
    let (_public_key) = public_key.read()

    # This interface expects a signature pointer and length to make
    # no assumption about signature validation schemes.
    # But this implementation does, and it expects a (sig_r, sig_s) pair.
    let sig_r = signature[0]
    let sig_s = signature[1]

    verify_ecdsa_signature(
        message=hash, public_key=_public_key, signature_r=sig_r, signature_s=sig_s)

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
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr,
        ecdsa_ptr : SignatureBuiltin*}(
        to : felt, selector : felt, calldata_len : felt, calldata : felt*, nonce : felt) -> (
        response_len : felt, response : felt*):
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
        calldata=message.calldata)

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
        res : felt):
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
func set_balance{
        syscall_ptr : felt*, 
        pedersen_ptr : HashBuiltin*, 
        range_check_ptr,
}(
    amount: felt
):
    let (curr_balance) = get_balance()
    balance.write(curr_balance + amount)
    return ()
end

# @notice Function to hash the order parameters
# @param message - Struct of order details to hash
# @param res - Hash of the details
func hash_order{pedersen_ptr : HashBuiltin*}(orderRequest : OrderRequest*) -> (res: felt):
    alloc_locals

    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (hash_state_ptr) = hash_init()
        # first three iterations are 'sender', 'to', and 'selector'
        let (hash_state_ptr) = hash_update(
            hash_state_ptr, 
            orderRequest, 
            7
        )
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
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    ecdsa_ptr : SignatureBuiltin*,
    range_check_ptr, 
}(
    request : OrderRequest,
    signature : Signature,
    size : felt,
    execution_price : felt
) -> (res : felt):
    alloc_locals
    let (__fp__, _) = get_fp_and_pc()

    # Make sure that the caller is the authorized Trading Contract
    let (caller) = get_caller_address()
    let (authorized_registry_) = authorized_registry.read()
    let (is_trading_contract) = IAuthorizedRegistry.get_registry_value(contract_address = authorized_registry_, address = caller, action = 3)
    assert is_trading_contract = 1

    # hash the parameters
    let (hash) = hash_order(&request)
    # check the validity of the signature
    is_valid_signature_order(hash, signature)

    tempvar status_
    # closeOrder == 0 -> Open a new position
    # closeOrder == 1 -> Close a position
    if request.closeOrder == 0:
        # Get the order details if already exists
        let (orderDetails) = order_mapping.read(orderID = request.orderID)
        # If it's a new order
        if orderDetails.ticker == 0:

            # Create if the order is being fully opened
            # status_ == 1, partially opened
            # status_ == 2, fully opened
            if request.positionSize == size:
                status_ = 2
            else :
                status_ = 1
            end

            # Create a new struct with the updated details
            let new_order = OrderDetails(
                ticker = request.ticker,
                price = request.price,
                executionPrice = execution_price,
                positionSize = request.positionSize,
                orderType = request.orderType,
                direction = request.direction,
                portionExecuted = size,
                status = status_
            )
            # Write to the mapping
            order_mapping.write(orderID = request.orderID, value = new_order)
            tempvar syscall_ptr :felt* = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 
            tempvar range_check_ptr = range_check_ptr
        # If it's an existing order
        else:
            # Return if the position size after the executing the current order is more than the order's positionSize
            assert_le(size + orderDetails.portionExecuted, request.positionSize)

            # Check if the order is the process of being closed
            assert_le(orderDetails.status, 2)

            # Check if the order is fully filled by executing the current one

            if request.positionSize == size + orderDetails.portionExecuted:
                status_ = 1
            else :
                status_ = 0
            end
            
            # Create a new struct with the updated details
            let updated_order = OrderDetails(
                ticker = orderDetails.ticker,
                price = orderDetails.price,
                executionPrice = orderDetails.executionPrice,
                positionSize = orderDetails.positionSize,
                orderType = request.orderType,
                direction = orderDetails.direction,
                portionExecuted = orderDetails.portionExecuted + size,
                status = status_
            )
            # Write to the mapping
            order_mapping.write(orderID = request.orderID, value = updated_order)
            tempvar syscall_ptr :felt* = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 
            tempvar range_check_ptr = range_check_ptr

        tempvar syscall_ptr :felt* = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 
        tempvar range_check_ptr = range_check_ptr
        end
    else :
        # Get the order details 
        let (orderDetails) = order_mapping.read(orderID = request.parentOrder)

        # Assert that it's the reverse direction of the current position
        assert_not_equal(request.direction, orderDetails.direction)

        # Assert that the order exists
        assert_not_zero(orderDetails.positionSize)
        assert_nn(orderDetails.portionExecuted - size)

        # Check if the order is fully closed or not
        # status_ == 4, fully closed
        # status_ == 3, partially closed
        if orderDetails.portionExecuted - size == 0:
            status_ = 4
        else :
            status_ = 3
        end

        # Create a new struct with the updated details
        let updated_order = OrderDetails(
            ticker = orderDetails.ticker,
            price = orderDetails.price,
            executionPrice = orderDetails.executionPrice,
            positionSize = orderDetails.positionSize,
            orderType = orderDetails.orderType,
            direction = orderDetails.direction,
            portionExecuted = orderDetails.portionExecuted - size,
            status = status_
        )
        
        # Write to the mapping 
        order_mapping.write(orderID = request.orderID, value = updated_order)

        tempvar syscall_ptr :felt* = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 
        tempvar range_check_ptr = range_check_ptr
    end

    return(1)
end

# @notice view function which checks the signature passed is valid
# @param hash - Hash of the order to check against 
# @param signature - Signature passed to the contract to check against
# @returns reverts, if there is an error
@view
func is_valid_signature_order{
        syscall_ptr : felt*, 
        pedersen_ptr : HashBuiltin*,
        range_check_ptr, 
        ecdsa_ptr: SignatureBuiltin*
    }(
        hash: felt,
        signature: Signature,
    ) -> ():
    let (_public_key) = public_key.read()
    let sig_r = signature.r_value
    let sig_s = signature.s_value

    verify_ecdsa_signature(
        message=hash,
        public_key=_public_key,
        signature_r=sig_r,
        signature_s=sig_s
    )

    return ()
end

# @notice AuthorizedRegistry interface
@contract_interface
namespace IAuthorizedRegistry:
    func get_registry_value(address : felt, action : felt) -> (allowed : felt):
    end
end

