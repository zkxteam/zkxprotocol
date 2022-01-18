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
    signature_2 : Signature
) -> (res : felt):
    assert (request1.direction * request2.direction) = 0
    assert (request1.direction + request2.direction) = 1
    assert (request1.price - request2.price) = 0
    assert (request1.ticker - request2.ticker) = 0
    assert_nn(request1.positionSize)
    assert_nn(request2.positionSize)


    let size_ = request2.positionSize
    let (res_) =  is_le(request1.positionSize, request2.positionSize)
    if (res_) == 1 :
        size_ = request1.positionSize
    end

    let (res1) = IAccount.place_order(contract_address=signer_1_pub_key, request = request1, signature = signature_1, size = size_)
    let (res2) = IAccount.place_order(contract_address=signer_2_pub_key, request = request2, signature = signature_2, size = size_)

    # transfer of funds
    #
    #
    #
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
end