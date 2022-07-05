%lang starknet

from contracts.interfaces.IMarkets import IMarkets
from contracts.libraries.RelayLibrary import (
    record_call_details,
    get_inner_contract,
    initialize,
    verify_caller_authority
)
from contracts.DataTypes import Market, MarketWID
from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.Constants import ManageMarkets_ACTION

# @notice - This will call initialize to set the registry address, version and index of underlying contract
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
    verify_caller_authority(ManageMarkets_ACTION)
    record_call_details('addMarket')
    let (inner_address)=get_inner_contract()
    IMarkets.addMarket(contract_address=inner_address,id=id,newMarket=newMarket)
    return()
end

@external
func removeMarket{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt
):
    verify_caller_authority(ManageMarkets_ACTION)
    record_call_details('removeMarket')
    let (inner_address)=get_inner_contract()
    IMarkets.removeMarket(contract_address=inner_address,id=id)
    return()
end

@external
func modifyLeverage{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt, leverage : felt
):
    verify_caller_authority(ManageMarkets_ACTION)
    record_call_details('modifyLeverage')
    let (inner_address)=get_inner_contract()
    IMarkets.modifyLeverage(contract_address=inner_address,id=id,leverage=leverage)
    return()
end


@external
func modifyTradable{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt, tradable : felt
):
    verify_caller_authority(ManageMarkets_ACTION)
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

@view
func getMarket_from_assets{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    asset_id : felt, collateral_id : felt
) -> (market_id : felt):
    
    let (inner_address)=get_inner_contract()
    let (market_id)=IMarkets.getMarket_from_assets(
        contract_address=inner_address,asset_id=asset_id, collateral_id=collateral_id)
    return(market_id)

end

@view
func returnAllMarkets{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    array_list_len : felt, array_list : MarketWID*
):

    let (inner_address)=get_inner_contract()
    let (array_list_len, array_list:MarketWID*)=IMarkets.returnAllMarkets(contract_address=inner_address)
    return(array_list_len, array_list)

end