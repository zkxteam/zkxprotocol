%lang starknet
%builtins pedersen range_check ecdsa

from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.common.syscalls import get_contract_address
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.starknet.common.syscalls import call_contract, get_caller_address, get_tx_signature
from starkware.cairo.common.hash_state import (
    hash_init, hash_finalize, hash_update, hash_update_single)
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.math import assert_le

#
# Structs
#

struct Message:
    member sender : felt
    member to : felt
    member selector : felt
    member calldata : felt*
    member calldata_size : felt
    member nonce : felt
end

struct OrderRequest:
    member orderID: felt
    member ticker: felt
    member price: felt
    member positionSize: felt
    member direction: felt
    member closeOrder: felt
end

struct Signature:
    member r_value: felt
    member s_value: felt
end

# status 0: partial
# status 1: executed
# status 2: close partial
# status 3: close
struct OrderDetails:
    member ticker: felt
    member price: felt
    member positionSize: felt
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
func get_order_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    order_ID : felt
) -> (
    res : OrderDetails
):
    let (res) = order_mapping.read(orderID=order_ID)
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

@external
func place_order{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr, 
    ecdsa_ptr: SignatureBuiltin*
}(
    request : OrderRequest,
    signature : Signature,
    size : felt
) -> (res : felt):
    alloc_locals
    let (__fp__, _) = get_fp_and_pc()

    # hash the parameters
    let (hash) = hash_order(&request)
    # check the validity of the signature
    is_valid_signature_order(hash, signature)
    
    # check if it's a partial order (Initial check)
    let (isPartial) = is_le(size, request.positionSize)
    
    # closeOrder == 0 -> Open a new position
    # closeOrder == 1 -> Close a position
    if request.closeOrder == 0:
        # Get the order details if already exists
        let (orderDetails) = order_mapping.read(orderID = request.orderID)
        # init var to store the order status
        if (isPartial) == 1:
            let status_ = 0
        else:
            let status_ = 1
        end
        
        # If it's a new order
        if orderDetails.ticker == 0:
            let new_order = OrderDetails(
                ticker = request.ticker,
                price = request.price,
                positionSize = request.positionSize,
                direction = request.direction,
                portionExecuted = size,
                status = status_
            )
            # Write to the mapping
            order_mapping.write(orderID = request.orderID, value = new_order)
        # If it's an existing order
        else:
            # Return if the position size after the executing the current order is more than the order's positionSize
            assert_le(request.positionSize, size + orderDetails.portionExecuted)
            # Check if the order is fully filled by executing the current one
            let (isPartialCurrent) = is_le(size + orderDetails.portionExecuted, request.positionSize)

            if (isPartialCurrent) == 0:
                status_ = 1
            end

            let updated_order = OrderDetails(
                ticker = orderDetails.ticker,
                price = orderDetails.price,
                positionSize = orderDetails.positionSize,
                direction = orderDetails.direction,
                portionExecuted = orderDetails.portionExecuted + size,
                status = status_
            )
            # Write to the mapping
            order_mapping.write(orderID = request.orderID, value = updated_order)
        end
    end

    return (1)
end

func hash_order{pedersen_ptr : HashBuiltin*}(orderRequest : OrderRequest*) -> (res: felt):
    alloc_locals

    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (hash_state_ptr) = hash_init()
        # first three iterations are 'sender', 'to', and 'selector'
        let (hash_state_ptr) = hash_update(
            hash_state_ptr, 
            orderRequest, 
            6
        )
        let (res) = hash_finalize(hash_state_ptr)
        let pedersen_ptr = hash_ptr
        return (res=res)
    end
end

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

    let sig_r = signature.r_value
    let sig_s = signature.s_value
    let (pub_key) = public_key.read()
    verify_ecdsa_signature(
        message=hash,
        public_key= pub_key,
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
