%lang starknet
%builtins pedersen range_check ecdsa

from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.common.syscalls import get_contract_address
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.starknet.common.syscalls import call_contract, get_caller_address, get_tx_signature
from starkware.cairo.common.hash_state import (
    hash_init, hash_finalize, hash_update, hash_update_single
)

#
# Structs
#

struct Message:
    member sender: felt
    member to: felt
    member selector: felt
    member calldata: felt*
    member calldata_size: felt
    member nonce: felt
end

# @notice structure to store Order Details
struct OrderDetails:
    member ticker: felt
    member orderType: felt
    member openingTimestamp: felt
    member openingPrice: felt
    member assetQuantity: felt
    member closingTimestamp: felt
    member closingPrice: felt
    member orderStatus: felt
end


#
# Storage
#

@storage_var
func current_nonce() -> (res: felt):
end

@storage_var
func public_key() -> (res: felt):
end

@storage_var
func trading_volume() -> (res: felt):
end

@storage_var
func balance() -> (res: felt):
end

# @notice Mapping between orderID and Account Portfolio
@storage_var
func order_details(orderId: felt) -> (order : OrderDetails):
end

# @notice Mapping between asset and assetquantity
@storage_var
func asset_details(asset: felt) -> (assetQuantity : felt):
end

#
# Guards
#

@view
func assert_only_self{
        syscall_ptr : felt*, 
        pedersen_ptr : HashBuiltin*,
        range_check_ptr
    }():
    let (self) = get_contract_address()
    let (caller) = get_caller_address()
    assert self = caller
    return ()
end

#
# Getters
#

@view
func get_public_key{
        syscall_ptr : felt*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr
    }() -> (res: felt):
    let (res) = public_key.read()
    return (res=res)
end

@view
func get_nonce{
        syscall_ptr : felt*, 
        pedersen_ptr : HashBuiltin*,
        range_check_ptr
    }() -> (res: felt):
    let (res) = current_nonce.read()
    return (res=res)
end

@view
func get_trading_volume{
        syscall_ptr : felt*, 
        pedersen_ptr : HashBuiltin*,
        range_check_ptr
    }() -> (res: felt):
    let (res) = trading_volume.read()
    return (res=res)
end

@view
func get_balance{
        syscall_ptr : felt*, 
        pedersen_ptr : HashBuiltin*,
        range_check_ptr
    }() -> (res: felt):
    let (res) = balance.read()
    return (res=res)
end

#
# Setters
#

@external
func set_public_key{
        syscall_ptr : felt*, 
        pedersen_ptr : HashBuiltin*,
        range_check_ptr
    }(new_public_key: felt):
    assert_only_self()
    public_key.write(new_public_key)
    return ()
end

#
# Constructor
#

@constructor
func constructor{
        syscall_ptr : felt*, 
        pedersen_ptr : HashBuiltin*,
        range_check_ptr
    }(_public_key: felt):
    public_key.write(_public_key)
    return()
end

#
# Business logic
#

@view
func is_valid_signature{
        syscall_ptr : felt*, 
        pedersen_ptr : HashBuiltin*,
        range_check_ptr, 
        ecdsa_ptr: SignatureBuiltin*
    }(
        hash: felt,
        signature_len: felt,
        signature: felt*
    ) -> ():
    let (_public_key) = public_key.read()

    # This interface expects a signature pointer and length to make
    # no assumption about signature validation schemes.
    # But this implementation does, and it expects a (sig_r, sig_s) pair.
    let sig_r = signature[0]
    let sig_s = signature[1]

    verify_ecdsa_signature(
        message=hash,
        public_key=_public_key,
        signature_r=sig_r,
        signature_s=sig_s)

    return ()
end

# @notice Getter function for order details
# @param orderID is the ID of the position
# @returns the position details associated with the order ID
@view
func getOrder{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}(orderId: felt) -> (order: OrderDetails) :

    let (orderDetails) = order_details.read(orderId = orderId)
    return (orderDetails)
end


# @notice Getter function for asset details
# @param asset 
# @returns the asset details
@view
func getAssetDetails{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}(asset: felt) -> (assetQuantity: felt) :

    let (assetQuantity) = asset_details.read(asset = asset)
    return (assetQuantity)
end

@external
func execute{
        syscall_ptr : felt*, 
        pedersen_ptr : HashBuiltin*,
        range_check_ptr, 
        ecdsa_ptr: SignatureBuiltin*
    }(
        to: felt,
        selector: felt,
        calldata_len: felt,
        calldata: felt*,
        nonce: felt
    ) -> (response_len: felt, response: felt*):
    alloc_locals

    let (__fp__, _) = get_fp_and_pc()
    let (_address) = get_contract_address()
    let (_current_nonce) = current_nonce.read()

    local message: Message = Message(
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
        calldata=message.calldata
    )

    return (response_len=response.retdata_size, response=response.retdata)
end

func hash_message{pedersen_ptr : HashBuiltin*}(message: Message*) -> (res: felt):
    alloc_locals
    # we need to make `res_calldata` local
    # to prevent the reference from being revoked
    let (local res_calldata) = hash_calldata(message.calldata, message.calldata_size)
    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (hash_state_ptr) = hash_init()
        # first three iterations are 'sender', 'to', and 'selector'
        let (hash_state_ptr) = hash_update(
            hash_state_ptr, 
            message, 
            3
        )
        let (hash_state_ptr) = hash_update_single(
            hash_state_ptr, res_calldata)
        let (hash_state_ptr) = hash_update_single(
            hash_state_ptr, message.nonce)
        let (res) = hash_finalize(hash_state_ptr)
        let pedersen_ptr = hash_ptr
        return (res=res)
    end
end

func hash_calldata{pedersen_ptr: HashBuiltin*}(
        calldata: felt*,
        calldata_size: felt
    ) -> (res: felt):
    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (hash_state_ptr) = hash_init()
        let (hash_state_ptr) = hash_update(
            hash_state_ptr,
            calldata,
            calldata_size
        )
        let (res) = hash_finalize(hash_state_ptr)
        let pedersen_ptr = hash_ptr
        return (res=res)
    end
end


# @notice Add order function
# @param orderId - ID of the order
# @param order details - struct variable with the required order details
@external
func addOrder{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}(orderId: felt, orderDetails: OrderDetails) :
    order_details.write(orderId = orderId, value = orderDetails)
    let asset = orderDetails.ticker
    let assetQuantity = orderDetails.assetQuantity
    let quantity: felt = asset_details.read(asset = asset)
    let totalQuantity = assetQuantity + quantity
    asset_details.write(asset = asset, value = totalQuantity)
    return ()
end


# @notice modify order function
# @param orderId - ID of the order
# @param modified order details - struct variable with the modified order details
@external
func modifyOrder{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}(orderId: felt, modifiedOrderDetails: OrderDetails) :
    order_details.write(orderId = orderId, value = modifiedOrderDetails)
    return ()
end