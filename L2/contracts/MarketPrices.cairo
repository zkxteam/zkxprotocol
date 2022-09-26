%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address

from contracts.Constants import (
    AdminAuth_INDEX,
    ManageMarkets_ACTION,
    Market_INDEX,
    MasterAdmin_ACTION,
    Trading_INDEX,
)
from contracts.DataTypes import Market, MarketPrice
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IMarkets import IMarkets
from contracts.libraries.Utils import verify_caller_authority

//#########
// Events #
//#########

// Event emitted whenever set_standard_collateral() is called
@event
func set_standard_collateral_called(collateral_id: felt) {
}

// Event emitted whenever update_market_price() is called
@event
func update_market_price_called(market_id: felt, price: felt) {
}

//##########
// Storage #
//##########

// Stores the contract version
@storage_var
func contract_version() -> (version: felt) {
}

// Stores the address of AuthorizedRegistry contract
@storage_var
func registry_address() -> (contract_address: felt) {
}

// Mapping between market ID and Market Prices
@storage_var
func market_prices(id: felt) -> (res: MarketPrice) {
}

// Stores the address of AuthorizedRegistry contract
@storage_var
func standard_collateral() -> (collateral_id: felt) {
}

//##############
// Constructor #
//##############

// @notice Constructor for the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    with_attr error_message("Registry address and version cannot be 0") {
        assert_not_zero(registry_address_);
        assert_not_zero(version_);
    }

    registry_address.write(value=registry_address_);
    contract_version.write(value=version_);
    return ();
}

//#################
// View Functions #
//#################

// @notice function to get market price
// @param market_id_ - Id of the market pair
@view
func get_market_price{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt
) -> (market_price: MarketPrice) {
    let (res) = market_prices.read(id=market_id_);
    return (market_price=res);
}

// @notice function to get standard collateral
// return collateral_id - standard collateral's collateral_id
@view
func get_standard_collateral{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    collateral_id: felt
) {
    let (res) = standard_collateral.read();
    return (collateral_id=res);
}

//#####################
// External Functions #
//#####################

// @notice function to set standard collateral
// @param collateral_id_ - standard collateral's collateral_id in the system
@external
func set_standard_collateral{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    collateral_id_: felt
) {
    // Check auth
    with_attr error_message("Caller is not authorized to set collateral price") {
        let (registry) = registry_address.read();
        let (version) = contract_version.read();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    standard_collateral.write(value=collateral_id_);

    // set_standard_collateral_called event is emitted
    set_standard_collateral_called.emit(collateral_id=collateral_id_);

    return ();
}

// @notice function to update market price
// @param market_id_ - Id of the market
// @param price_ - price of the market pair
@external
func update_market_price{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, price_: felt
) {
    let (caller) = get_caller_address();
    let (registry) = registry_address.read();
    let (version) = contract_version.read();

    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    );

    // Auth Check
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=ManageMarkets_ACTION
    );

    if (access == 0) {
        // Get trading contract address
        let (trading_contract_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=Trading_INDEX, version=version
        );

        with_attr error_message("Caller is not authorized to update market price") {
            assert caller = trading_contract_address;
        }

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    let (registry) = registry_address.read();
    let (version) = contract_version.read();

    // Calculate the timestamp
    let (timestamp_) = get_block_timestamp();

    // Get market contract address
    let (market_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get Market from the corresponding Id
    let (market: Market) = IMarkets.getMarket(
        contract_address=market_contract_address, id=market_id_
    );

    // Create a struct object for the market prices
    tempvar new_market_price: MarketPrice = MarketPrice(
        asset_id=market.asset,
        collateral_id=market.assetCollateral,
        timestamp=timestamp_,
        price=price_,
        );

    market_prices.write(id=market_id_, value=new_market_price);

    // update_market_price_called event is emitted
    update_market_price_called.emit(market_id=market_id_, price=price_);

    return ();
}
