%lang starknet

from contracts.interfaces.IMarkets import IMarkets
from contracts.libraries.RelayLibrary import (
    record_call_details,
    get_inner_contract,
    initialize
)
from contracts.DataTypes import Market
from starkware.cairo.common.cairo_builtins import HashBuiltin


# @notice - This will call initialize to set the registrey address, version and index of underlying contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt, index_:felt):

    initialize(registry_address_,version_,index_)
    return ()
end

# @notice - All the following are mirror functions for Markets.cairo - just record call details and forward call

@external
func addMarket{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
            id : felt, newMarket : Market
):
    record_call_details('addMarket')
    let (inner_address)=get_inner_contract()
    IMarkets.addMarket(contract_address=inner_address,id=id,newMarket=newMarket)
    return()
end

@external
func removeMarket{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt
):
    record_call_details('removeMarket')
    let (inner_address)=get_inner_contract()
    IMarkets.removeMarket(contract_address=inner_address,id=id)
    return()
end

@external
func modifyLeverage{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt, leverage : felt
):
    record_call_details('modifyLeverage')
    let (inner_address)=get_inner_contract()
    IMarkets.modifyLeverage(contract_address=inner_address,id=id,leverage=leverage)
    return()
end


@external
func modifyTradable{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt, tradable : felt
):
    record_call_details('modifyTradable')
    let (inner_address)=get_inner_contract()
    IMarkets.modifyTradable(contract_address=inner_address,id=id,tradable=tradable)
    return()
end


@view
func getMarket{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt
) -> (currMarket : Market):

    let (inner_address)=get_inner_contract()
    let (currMarket)=IMarkets.getMarket(contract_address=inner_address,id=id)
    return(currMarket)
end