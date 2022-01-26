%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.math import assert_not_zero, assert_nn, assert_le
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.hash_state import (
    hash_init, hash_finalize, hash_update
)

@storage_var
func balance() -> (res : felt):
end

@storage_var
func asset_contract_address() -> (res : felt):
end

@storage_var
func trading_contract_address() -> (res : felt):
end

struct MultipleOrder:
    member pub_key: felt
    member sig_r: felt
    member sig_s: felt
    member orderID: felt
    member ticker: felt
    member price: felt
    member positionSize: felt
    member direction: felt
    member closeOrder: felt
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

# @notice struct to store details of assets
struct Asset:
    member ticker: felt
    member short_name: felt
    member tradable: felt
end

@storage_var
func asset_mapping(id : felt) -> (asset : MultipleOrder):
end


@view
func get_asset{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}(id: felt) -> (asset : MultipleOrder):
    let (asset) = asset_mapping.read(id=id)
    return (asset)
end

@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    _asset_contract, _trading_fees):
    asset_contract_address.write(_asset_contract)
    trading_contract_address.write(_trading_fees)
    return ()
end

@external
func execute_order{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr, 
    ecdsa_ptr: SignatureBuiltin*
}(
    request1 : OrderRequest,
    signer_1_pub_key : felt,
    signature_1 : Signature,
    request2 : OrderRequest,
    signer_2_pub_key : felt,
    signature_2 : Signature,
    size : felt
) -> (res : felt):
    assert (request1.direction * request2.direction) = 0
    assert (request1.direction + request2.direction) = 1
    assert (request1.price - request2.price) = 0
    assert (request1.ticker - request2.ticker) = 0
    assert_nn(request1.positionSize)
    assert_nn(request2.positionSize)

    let (res1) = IAccount.place_order(contract_address=signer_1_pub_key, request = request1, signature = signature_1, size = size)
    let (res2) = IAccount.place_order(contract_address=signer_2_pub_key, request = request2, signature = signature_2, size = size)

    return (1)
end


func perform_checks{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr, 
}(  
    size : felt,
    ticker : felt,
    price : felt,
    request_list_len : felt,
    request_list :  MultipleOrder*,
    long_fees : felt,
    short_fees : felt
) -> (res : felt):
    alloc_locals

    # Check if the list is empty, if yes return 1
    if request_list_len == 0:
        return (1)
    end

    # Create a struct object for the order 
    tempvar temp_order: MultipleOrder = MultipleOrder(
        pub_key = [request_list].pub_key,
        sig_r = [request_list].sig_r,
        sig_s = [request_list].sig_s,
        orderID = [request_list].orderID,
        ticker = [request_list].ticker,
        price = [request_list].price,
        positionSize = [request_list].positionSize,
        direction = [request_list].direction,
        closeOrder = [request_list].closeOrder
    )

    # Assert that the size of the order is less than or equal to the positionSize in the Order
    assert_le(size, temp_order.positionSize)

    tempvar fees
    
    # Calculate the fees depending on whether the order is long or short
    if temp_order.direction == 1:
        fees = long_fees
    else :
        fees = short_fees
    end

    # Calculate the amount of USDC required to execute the order
    tempvar total_fees = temp_order.price * size * fees
    tempvar amount = temp_order.price * size 
    tempvar total_amount = total_fees + amount

    # Create a temporary order object
    let temp_order_request : OrderRequest = OrderRequest(
        orderID = temp_order.orderID,
        ticker = temp_order.ticker,
        price = temp_order.price,
        positionSize = temp_order.positionSize,
        direction = temp_order.direction,
        closeOrder = temp_order.closeOrder
    )

    # Create a temporary signature object
    let temp_signature : Signature = Signature(
        r_value = temp_order.sig_r,
        s_value = temp_order.sig_s
    )
    
    # Call the account contract to initialize the order
    IAccount.initialize_order(
        contract_address = temp_order.pub_key, 
        request = temp_order_request, 
        signature = temp_signature, 
        size = size, 
        amount = total_amount
    )  

    # If it's the first order in the array
    if ticker == 0:
        # Check if the asset is tradable 
        let (asset_address) = asset_contract_address.read()
        let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=temp_order_request.ticker)

        # tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 
        assert_not_zero(asset.tradable)

        # Recursive call with the ticker and price to compare against
        return perform_checks(
            size,
            temp_order.ticker,
            temp_order.price,
            request_list_len - 1,
            request_list + MultipleOrder.SIZE,
            long_fees,
            short_fees
        )
    end

    # Assert that the order has the same ticker and price as the first order
    assert ticker = temp_order.ticker
    assert price = temp_order.price
   
   # TODO: REMOVE testing purpose 
    asset_mapping.write(id=request_list_len, value=temp_order)

    # Recursive Call
    return perform_checks(
        size,
        ticker,
        price,
        request_list_len - 1,
        request_list + MultipleOrder.SIZE,
        long_fees,
        short_fees
    )
end

@external
func check_execution{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr, 
    ecdsa_ptr: SignatureBuiltin*
}(    
    size : felt,
    request_list_len : felt,
    request_list : MultipleOrder*,
) -> (res : felt):
    alloc_locals
    
    assert_not_zero(size)

    let (fees_address) = trading_contract_address.read()
    let (long, short) = ITradingFees.get_fees(contract_address=fees_address)
    
    assert_not_zero(long)
    assert_not_zero(short)

    local long_fee = long
    local short_fee = short

    let (result) = perform_checks(
        size, 
        0,
        0,
        request_list_len, 
        request_list, 
        long_fee,
        short_fee
        
    )
    
    return (result)
end
    # assert (request1.direction * request2.direction) = 0
    # assert (request1.direction + request2.direction) = 1
    # assert (request1.price - request2.price) = 0
    # assert (request1.ticker - request2.ticker) = 0
    # assert_nn(request1.positionSize)
    # assert_nn(request2.positionSize)

    # tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 
    # let (asset_address) = asset_contract_address.read()
    # let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=request1.ticker)

    # # tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 

    # assert_not_zero(asset.tradable)
    # let (fees_address) = trading_contract_address.read()
    # let (long, short) = ITradingFees.get_fees(contract_address=fees_address)

    # local fees1
    # local fees2
    # if request1.direction == 0:
    #     fees1 = long
    #     fees2 = short
    # else:
    #     fees1 = short
    #     fees2 = long
    # end

    # let total_amount1 = fees1 * size * request1.price
    # let total_amount2 = fees2 * size * request2.price

    # let (res1) = IAccount.initialize_order(contract_address=signer_1_pub_key, request = request1, signature = signature_1, size = size, amount = total_amount1)
    # let (res2) = IAccount.initialize_order(contract_address=signer_2_pub_key, request = request2, signature = signature_2, size = size, amount = total_amount2)


@contract_interface
namespace IAccount:
    func place_order(
        request : OrderRequest,
        signature : Signature,
        size : felt
    ) -> (res : felt):
    end

    func initialize_order(
        request : OrderRequest,
        signature : Signature,
        size : felt,
        amount : felt
    ) -> (res : felt):
    end
end


# @notice TradingFees interface
@contract_interface
namespace ITradingFees:
    func get_fees() -> (
        long_fees: felt, 
        short_fees: felt
    ):
    end 
end

# @notice Asset interface
@contract_interface
namespace IAsset:
    func getAsset(id: felt) -> (
        currAsset: Asset
    ):
    end
end