%lang starknet

from starkware.cairo.common.bool import FALSE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_nn, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address

from contracts.Constants import AdminAuth_INDEX, ManageMarkets_ACTION, Market_INDEX, Trading_INDEX
from contracts.DataTypes import Market, MarketPrice, MultipleMarketPrices
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IMarkets import IMarkets
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_assert64x61

// //////////
// Events //
// //////////

// Event emitted whenever update_market_price() is called
@event
func update_market_price_called(market_id: felt, price: felt) {
}

// ///////////
// Storage //
// ///////////

// Mapping between market ID and Market Prices
@storage_var
func market_prices(id: felt) -> (res: MarketPrice) {
}

// ///////////////
// Constructor //
// ///////////////

// @notice Constructor for the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    return ();
}

// ////////
// View //
// ////////

// @notice function to get market price
// @param market_id_ - Id of the market pair
@view
func get_market_price{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt
) -> (market_price: felt) {
    // Get registry and version of the Authorized Registry
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get the address of the market contract
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get the market ttl from the market contract
    let (market_ttl: felt) = IMarkets.get_ttl_from_market(
        contract_address=market_address, market_id_=market_id_
    );

    // Get market price structure of the specified market id
    let (market_price: MarketPrice) = market_prices.read(market_id_);

    // Calculate the timestamp
    let (current_timestamp) = get_block_timestamp();
    let ttl = market_ttl;
    let timestamp = market_price.timestamp;
    let time_difference = current_timestamp - timestamp;

    let status = is_le(time_difference, ttl);
    // ttl has passed, return 0
    if (status == FALSE) {
        return (0,);
    } else {
        let price = market_price.price;
        return (price,);
    }
}

// ////////////
// External //
// ////////////

// @notice function to update market price
// @param market_id_ - Id of the market
// @param price_ - price of the market pair
@external
func update_market_price{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, price_: felt
) {
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

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

        with_attr error_message("MarketPrices: Unauthorized caller for updating market price") {
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

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Calculate the timestamp
    let (timestamp_) = get_block_timestamp();

    // Get market contract address
    let (market_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get Market from the corresponding Id
    let (market: Market) = IMarkets.get_market(
        contract_address=market_contract_address, market_id_=market_id_
    );

    with_attr error_message("MarketPrices: Price cannot be negative") {
        assert_nn(price_);
    }

    with_attr error_message("MarketPrices: Price must be in 64x61 respresentation") {
        Math64x61_assert64x61(price_);
    }

    with_attr error_message("MarketPrices: Market does not exist") {
        assert_not_zero(market.asset);
    }

    // Create a struct object for the market prices
    tempvar new_market_price: MarketPrice = MarketPrice(
        asset_id=market.asset,
        collateral_id=market.asset_collateral,
        timestamp=timestamp_,
        price=price_,
    );

    market_prices.write(id=market_id_, value=new_market_price);

    // update_market_price_called event is emitted
    update_market_price_called.emit(market_id=market_id_, price=price_);

    return ();
}

// @notice function to update multiple market prices
// @notice This function is called by update_multiple_market_prices
// @param market_prices_len - Length of market prices array
// @param market_prices - Market prices array
@external
func update_multiple_market_prices{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_prices_len: felt, market_prices: MultipleMarketPrices*
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    verify_caller_authority(registry, version, ManageMarkets_ACTION);

    // Calculate the timestamp
    let (timestamp) = get_block_timestamp();

    // Get market contract address
    let (market_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    return update_market_prices_recurse(
        market_contract_address_=market_contract_address,
        timestamp_=timestamp,
        iterator_=0,
        market_prices_len=market_prices_len,
        market_prices=market_prices,
    );
}

// ///////////
// Internal //
// ///////////

// @notice This function is called by update_multiple_market_prices
// @param market_contract_address_ - Address of the market contract address
// @param timestamp_ - Current timestamp
// @param iterator_ -  Current index of the market ids array
// @param market_prices_len - Length of market prices array
// @param market_prices - Market prices array
func update_market_prices_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_contract_address_: felt,
    timestamp_: felt,
    iterator_: felt,
    market_prices_len: felt,
    market_prices: MultipleMarketPrices*,
) {
    alloc_locals;
    // Termination conditon
    if (iterator_ == market_prices_len) {
        return ();
    }

    // Get Market from the corresponding Id
    let (market: Market) = IMarkets.get_market(
        contract_address=market_contract_address_, market_id_=market_prices[iterator_].market_id
    );

    with_attr error_message("MarketPrices: Price cannot be negative") {
        assert_nn(market_prices[iterator_].price);
    }

    with_attr error_message("MarketPrices: Price must be in 64x61 respresentation") {
        Math64x61_assert64x61(market_prices[iterator_].price);
    }

    with_attr error_message("MarketPrices: Market does not exist") {
        assert_not_zero(market.asset);
    }

    // Create a struct object for the market prices
    tempvar new_market_price: MarketPrice = MarketPrice(
        asset_id=market.asset,
        collateral_id=market.asset_collateral,
        timestamp=timestamp_,
        price=market_prices[iterator_].price,
    );

    market_prices.write(id=market_prices[iterator_].market_id, value=new_market_price);

    return update_market_prices_recurse(
        market_contract_address_,
        market_contract_address_=market_contract_address_,
        timestamp_=timestamp_,
        iterator_=iterator_ + 1,
        market_prices_len=market_prices_len,
        market_prices=market_prices,
    );
}
