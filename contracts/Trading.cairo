%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.common.syscalls import get_contract_address
from starkware.cairo.common.math import assert_not_zero, assert_nn, assert_le, assert_in_range
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

# Struct to pass orders+signatures in a batch in the execute_batch fn
struct MultipleOrder:
    member pub_key: felt
    member sig_r: felt
    member sig_s: felt
    member orderID: felt
    member ticker: felt
    member price: felt
    member orderType: felt
    member positionSize: felt
    member direction: felt
    member closeOrder: felt
    member parentOrder: felt
end

# Struct for passing the order request to Account Contract
struct OrderRequest:
    member orderID: felt
    member ticker: felt
    member price: felt
    member orderType: felt
    member positionSize: felt
    member direction: felt
    member closeOrder: felt
    member parentOrder: felt
end

# Struct for passing signature to Account Contract
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

# @notice Constructor for the contract
# @param _asset_contract - Address of the deployed address contract
# @param _trading_fees - Address of the deployed tradingfees contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    _asset_contract, _trading_fees):
    asset_contract_address.write(_asset_contract)
    trading_contract_address.write(_trading_fees)
    return ()
end

# @notice Internal function called by execute_batch
# @param size - Size of the order to be executed
# @param ticker - The ticker of each order in the batch
# @param execution_price - Price at which the orders must be executed
# @param request_list_len - No of orders in the batch
# @param request_list - The batch of the orders
# @returns 1, if executed correctly
func check_and_execute{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr, 
}(  
    size : felt,
    ticker : felt,
    execution_price : felt,
    request_list_len : felt,
    request_list :  MultipleOrder*,
    long_fees : felt,
    short_fees : felt
) -> (res : felt):
    alloc_locals

    # Check if the list is empty, if yes return 1
    if request_list_len == 0:
        return (0)
    end

    # Create a struct object for the order 
    tempvar temp_order: MultipleOrder = MultipleOrder(
        pub_key = [request_list].pub_key,
        sig_r = [request_list].sig_r,
        sig_s = [request_list].sig_s,
        orderID = [request_list].orderID,
        ticker = [request_list].ticker,
        price = [request_list].price,
        orderType = [request_list].orderType,
        positionSize = [request_list].positionSize,
        direction = [request_list].direction,
        closeOrder = [request_list].closeOrder,
        parentOrder = [request_list].parentOrder
    )

    # Check if the execution_price is correct
    if temp_order.orderType == 0:
        # if it's a market order, it must be within 2% of the index price
        tempvar two_percent = (temp_order.price * 20000) / 10**6
        tempvar lowerLimit = temp_order.price + two_percent
        tempvar upperLimit = temp_order.price - two_percent
        # assert_in_range(execution_price, lowerLimit, upperLimit)
        tempvar range_check_ptr = range_check_ptr
    else:
        # if it's a limit order 
        if temp_order.direction == 1:
            # if it's a long order
            assert_le(execution_price, temp_order.price)
            tempvar range_check_ptr = range_check_ptr
        else:
            # if it's a short order
            assert_le(temp_order.price, temp_order.price)
            tempvar range_check_ptr = range_check_ptr
        end
        tempvar range_check_ptr = range_check_ptr
    end


    local fees_rate   
    # Calculate the fees depending on whether the order is long or short
    if temp_order.direction == 1:
        assert fees_rate = long_fees
    else :
        assert fees_rate = short_fees
    end

    # Check if size is less than or equal to postionSize
    let (cmp_res) = is_le(size, temp_order.positionSize)

    local order_size
    

    if cmp_res == 1:
        # If yes, make the order_size to be size
        assert order_size = size
    else :
        # If no, make order_size to be the positionSize
        assert order_size = temp_order.positionSize
    end
    
    # Calculate the fees for the order
    tempvar fees = (execution_price * order_size * fees_rate) / 10**12
    tempvar amount = (temp_order.price * order_size) / 10**6

    # Amount the user must pay
    tempvar total_amount = fees + amount

    # TODO: Transfer of funds for acc long/short or open/close

    # if temp_order.direction == 1:
    #     if temp_order.closeOrder == 0:
    #        let (contract_address) = get_contract_address()
    #         let (approved) = IAccount.get_allowance(contract_address = temp_order.pub_key, address_ = contract_address)
    #         assert_le(total_amount, approved)
    #         tempvar syscall_ptr :felt* = syscall_ptr
    #         tempvar range_check_ptr = range_check_ptr
    #     end
    # end
            

    # Create a temporary order object
    let temp_order_request : OrderRequest = OrderRequest(
        orderID = temp_order.orderID,
        ticker = temp_order.ticker,
        price = temp_order.price,
        orderType = temp_order.orderType,
        positionSize = temp_order.positionSize,
        direction = temp_order.direction,
        closeOrder = temp_order.closeOrder,
        parentOrder = [request_list].parentOrder
    )

    # Create a temporary signature object
    let temp_signature : Signature = Signature(
        r_value = temp_order.sig_r,
        s_value = temp_order.sig_s
    )
    
    # Call the account contract to initialize the order
    IAccount.execute_order(
        contract_address = temp_order.pub_key, 
        request = temp_order_request, 
        signature = temp_signature, 
        size = order_size, 
        execution_price = execution_price,
        amount = total_amount,
        
    )  

    # If it's the first order in the array
    if ticker == 0:
        # Check if the asset is tradable 
        let (asset_address) = asset_contract_address.read()
        let (asset : Asset) = IAsset.getAsset(contract_address = asset_address, id = temp_order.ticker)

        # tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 
        assert_not_zero(asset.tradable)

        # Recursive call with the ticker and price to compare against
        return check_and_execute(
            size,
            temp_order.ticker,
            execution_price,
            request_list_len - 1,
            request_list + MultipleOrder.SIZE,
            long_fees,
            short_fees
        )
    end

    # Assert that the order has the same ticker and price as the first order
    assert ticker = temp_order.ticker
   
    # Recursive Call
    return check_and_execute(
        size,
        ticker,
        execution_price,
        request_list_len - 1,
        request_list + MultipleOrder.SIZE,
        long_fees,
        short_fees
    )
end

# @notice Function to execute multiple orders in a batch
# @param size - Size of the order to be executed
# @param execution_price - Price at which the orders must be executed
# @param request_list_len - No of orders in the batch
# @param request_list - The batch of the orders
# @returns res - 1 if executed correctly
@external
func execute_batch{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr, 
    ecdsa_ptr: SignatureBuiltin*
}(    
    size : felt,
    execution_price : felt,
    request_list_len : felt,
    request_list : MultipleOrder*,
) -> (res : felt):
    alloc_locals
    
    # Assert that the execution size is not 0
    assert_not_zero(size)

    # Fetch the base fees for long and short orders
    let (fees_address) = trading_contract_address.read()
    let (long, short) = ITradingFees.get_fees(contract_address=fees_address)
    
    # Assert that these fees are not 0
    assert_not_zero(long)
    assert_not_zero(short)

    # Store it in a local var to send it to check_and_execute
    local long_fee = long
    local short_fee = short

    # Recursively loop through the orders in the batch
    let (result) = check_and_execute(
        size, 
        0,
        execution_price,
        request_list_len, 
        request_list, 
        long_fee,
        short_fee
    )

    return (result)
end

# @notice Account interface
@contract_interface
namespace IAccount:
    func execute_order(
        request : OrderRequest,
        signature : Signature,
        size : felt,
        execution_price : felt,
        amount : felt
    ) -> (res : felt):
    end

    func transfer_from(
        amount : felt
    ) -> ():
    end


    func get_allowance(
        address_ : felt
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