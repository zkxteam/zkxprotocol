%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.math import assert_not_zero, assert_nn
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

@external
func check_execution{
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
    alloc_locals
    assert (request1.direction * request2.direction) = 0
    assert (request1.direction + request2.direction) = 1
    assert (request1.price - request2.price) = 0
    assert (request1.ticker - request2.ticker) = 0
    assert_nn(request1.positionSize)
    assert_nn(request2.positionSize)

    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 
    let (asset_address) = asset_contract_address.read()
    let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=request1.ticker)

    # tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr 

    assert_not_zero(asset.tradable)
    let (fees_address) = trading_contract_address.read()
    let (long, short) = ITradingFees.get_fees(contract_address=fees_address)

    local fees1
    local fees2
    if request1.direction == 0:
        fees1 = long
        fees2 = short
    else:
        fees1 = short
        fees2 = long
    end

    let total_amount1 = fees1 * size * request1.price
    let total_amount2 = fees2 * size * request2.price

    let (res1) = IAccount.initialize_order(contract_address=signer_1_pub_key, request = request1, signature = signature_1, size = size, amount = total_amount1)
    let (res2) = IAccount.initialize_order(contract_address=signer_2_pub_key, request = request2, signature = signature_2, size = size, amount = total_amount2)

    return (1)
end

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