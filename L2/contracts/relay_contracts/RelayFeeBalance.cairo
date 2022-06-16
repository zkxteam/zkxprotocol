%lang starknet

from contracts.interfaces.IFeeBalance import IFeeBalance
from contracts.libraries.RelayLibrary import (
    record_call_details,
    get_inner_contract,
    initialize
)

from starkware.cairo.common.cairo_builtins import HashBuiltin


# @notice - This will call initialize to set the registry address, version and index of underlying contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt, index_:felt):

    initialize(registry_address_,version_,index_)
    return ()
end

# @notice - All the following are mirror functions for FeeBalance.cairo - just record call details and forward call

@external
func update_fee_mapping{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt, assetID_ : felt, fee_to_add : felt
):
    record_call_details('update_fee_mapping')
    let (inner_address)=get_inner_contract()
    IFeeBalance.update_fee_mapping(inner_address, address, assetID_, fee_to_add)
    return()
end


@view
func get_total_fee{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt
) -> (fee : felt):

    let (inner_address)=get_inner_contract()
    let (res)=IFeeBalance.get_total_fee(inner_address, assetID_)
    return(res)
end

@view
func get_user_fee{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address : felt, assetID_ : felt
) -> (fee : felt):
    let (inner_address)=get_inner_contract()
    let (res)=IFeeBalance.get_user_fee(inner_address,address, assetID_)
    return(res)
end
