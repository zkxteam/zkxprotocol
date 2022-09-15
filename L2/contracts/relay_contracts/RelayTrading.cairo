%lang starknet

from contracts.interfaces.ITrading import ITrading
from contracts.libraries.RelayLibrary import record_call_details, get_inner_contract, initialize
from contracts.DataTypes import MultipleOrder
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin

# @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt, index_ : felt
):
    initialize(registry_address_, version_, index_)
    return ()
end

# @notice - All the following are mirror functions for Trading.cairo - just record call details and forward call

@external
func execute_batch{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(
    size_ : felt,
    execution_price_ : felt,
    marketID_ : felt,
    request_list_len : felt,
    request_list : MultipleOrder*,
):
    alloc_locals

    local pedersen_ptr : HashBuiltin* = pedersen_ptr
    local range_check_ptr = range_check_ptr
    local ecdsa_ptr : SignatureBuiltin* = ecdsa_ptr

    record_call_details('execute_batch')
    let (inner_address) = get_inner_contract()
    ITrading.execute_batch(
        inner_address, size_, execution_price_, marketID_, request_list_len, request_list
    )
    return ()
end
