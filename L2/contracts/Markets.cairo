%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_le_felt, assert_nn, assert_not_zero
from starkware.cairo.common.math_cmp import is_le

from contracts.Constants import Asset_INDEX, ManageMarkets_ACTION
from contracts.DataTypes import Asset, Market
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from contracts.libraries.Validation import assert_bool
from contracts.Math_64x61 import Math64x61_assert64x61, Math64x61_ONE

///////////////
// Constants //
///////////////

const MAX_TRADABLE = 2;
const MIN_LEVERAGE = Math64x61_ONE;

////////////
// Events //
////////////

// Event emitted whenever a new market is added
@event
func market_added(market_id: felt, market: Market) {
}

// Event emitted whenever a market is removed
@event
func market_removed(market_id: felt) {
}

// Event emitted whenever a market's leverage is modified
@event
func market_leverage_modified(market_id: felt, leverage: felt) {
}

// Event emitted whenever a market's tradable parameter is modified
@event
func market_tradable_modified(market_id: felt, tradable: felt) {
}

// Event emitted whenever a market's archived parameter is modified
@event
func market_archived_state_modified(market_id: felt, archived: felt) {
}

/////////////
// Storage //
/////////////

// Stores the max leverage possible in the system
@storage_var
func max_leverage() -> (leverage: felt) {
}

// Stores the max ttl for a market in the system
@storage_var
func max_ttl() -> (ttl: felt) {
}

// Version of Market contract to refresh in node
@storage_var
func version() -> (res: felt) {
}

// Length of the markets array
@storage_var
func markets_array_len() -> (len: felt) {
}

// Markets in an array to enable retrieval from node
@storage_var
func market_id_by_index(index: felt) -> (market_id: felt) {
}

// Mapping between market ID and market's index
@storage_var
func market_index_by_id(market_id: felt) -> (index: felt) {
}

// Mapping between market ID and Market's data
@storage_var
func market_by_id(market_id: felt) -> (res: Market) {
}

// Bool indicating if ID already exists
@storage_var
func market_id_exists(market_id: felt) -> (res: felt) {
}

// Mapping between assetID, collateralID and MarketID
@storage_var
func market_mapping(asset_id: felt, collateral_id: felt) -> (res: felt) {
}

// Bool indicating if ticker-pair already exists
@storage_var
func market_pair_exists(asset: felt, assetCollateral: felt) -> (res: felt) {
}

/////////////////
// Constructor //
/////////////////

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    max_leverage.write(10 * Math64x61_ONE);
    max_ttl.write(3600);
    return ();
}

//////////
// View //
//////////

// @notice Gets a list of all markets
// @returns array_list_len - Length of the markets list
// @returns array_list - Fully populated list of markets
@view
func get_all_markets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    array_list_len: felt, array_list: MarketWID*
) {
    alloc_locals;

    let (array_list: MarketWID*) = alloc();
    let (array_list_len) = markets_array_len.read();
    return populate_markets(iterator=0, array_list_len=array_list_len, array_list=array_list);
}

// @notice Gets Market struct by its ID
// @param market_id_ - Market ID
// @return currMarket - Returns the requested Market struct
@view
func get_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt
) -> (currMarket: Market) {
    let (currMarket) = market_by_id.read(market_id_);
    return (currMarket,);
}

// @notice Gets a maintenance margin for a market
// @param market_id_ - Market ID
// @return maintenance_margin - Returns a maintenance margin of the market
@view
func get_maintenance_margin{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt
) -> (maintenance_margin: felt) {
    let (currMarket) = market_by_id.read(market_id_);
    return (currMarket.maintenance_margin_fraction,);
}

// @notice Gets market ID for associated Asset and Collateral IDs
// @param asset_id_ - Asset ID
// @param collateral_id_ - Collateral ID
// @return market_id - Returns the requested market ID
@view
func get_market_id_from_assets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, collateral_id_: felt
) -> (market_id: felt) {
    let (market_id) = market_mapping.read(asset_id=asset_id_, collateral_id=collateral_id_);
    return (market_id,);
}

// @notice Gets collateral asset by market ID
// @param market_id_ - Market ID
// @returns collateral_id - Collateral ID of the market
@view
func get_collateral_from_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt
) -> (collateral_id: felt) {
    let (currMarket) = market_by_id.read(market_id_);
    return (currMarket.asset_collateral,);
}

// @notice Gets asset-collateral pair IDs by market ID
// @param market_id_ - Market ID
// @returns asset_id - Asset ID of the market
// @returns collateral_id - Collateral ID of the market
@view
func get_asset_collateral_from_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt
) -> (asset_id: felt, collateral_id: felt) {
    let (currMarket) = market_by_id.read(market_id_);
    return (currMarket.asset, currMarket.asset_collateral);
}

// @notice Gets a ttl value of the market
// @param market_id_ - Market ID
// @returns ttl - ttl of the market
@view
func get_ttl_from_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt
) -> (ttl: felt) {
    let (currMarket) = market_by_id.read(market_id_);
    return (currMarket.ttl,);
}

// @notice Gets all markets with matching tradable and archived state with IDs in a list
// @param is_tradable_ - tradable flag
// @param is_archived_ - archived flag
// @returns array_list_len - Length of the array_list
// @returns array_list - Fully populated list of MarketWID
@view
func get_all_markets_by_state{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    is_tradable_: felt, is_archived_: felt
) -> (array_list_len: felt, array_list: Market*) {
    alloc_locals;

    let (array_list: MarketWID*) = alloc();
    let (array_list_len) = markets_array_len.read();
    return populate_markets_by_state(
        iterator=0,
        index=0,
        is_tradable=is_tradable_,
        is_archived=is_archived_,
        array_list_len=array_list_len,
        array_list=array_list,
    );
}

//////////////
// External //
//////////////

// @notice Function called by admin to change the max leverage allowed in the system
// @param new_max_leverage - New maximmum leverage
@external
func change_max_leverage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_max_leverage_: felt
) {
    verify_market_manager_authority();
    with_attr error_message("Markets: Max leverage must be >= MIN leverage") {
        assert_le(MIN_LEVERAGE, new_max_leverage_);
    }
    max_leverage.write(new_max_leverage_);
    return ();
}

// @notice Function called by admin to change the max ttl allowed in the system
// @param new_max_ttl - New maximum ttl
@external
func change_max_ttl{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_max_ttl_: felt
) {
    verify_market_manager_authority();
    with_attr error_message("Markets: Max ttl cannot be 0") {
        assert_not_zero(new_max_ttl_);
    }
    max_ttl.write(new_max_ttl_);
    return ();
}

// @notice Add market function
// @param new_market_ - Market struct variable with the required details
// if tradable value of new_market_ = 2, it means take value from Asset contract
@external
func add_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_market_: Market
) {
    alloc_locals;

    // Verification
    verify_market_manager_authority();
    verify_market_id_exists(new_market_.id, should_exist_=FALSE);
    with_attr error_message("Markets: Market pair existence check failed") {
        let (pair_exists) = market_pair_exists.read(new_market_.asset, new_market_.asset_collateral);
        assert pair_exists = FALSE;
    }

    // Validation
    validate_market_properties(new_market_);
    validate_market_trading_settings(new_market_);
    
    let (new_tradable) = resolve_tradable_status(new_market_);

    // Save market to storage
    market_by_id.write(
        market_id=new_market_.id,
        value=Market(
            market_id=new_market_.id,
            value=Market(id=new_market_.id,
            asset=new_market_.asset, 
            asset_collateral=new_market_.asset_collateral, 
            leverage=new_market_.leverage, 
            is_tradable=new_tradable, 
            is_archived=new_market_.is_archived, 
            ttl=new_market_.ttl, 
            tick_size=new_market_.tick_size,
            step_size=new_market_.step_size,
            minimum_order_size=new_market_.minimum_order_size,
            minimum_leverage=new_market_.minimum_leverage,
            maximum_leverage=new_market_.maximum_leverage,
            currently_allowed_leverage=new_market_.currently_allowed_leverage,
            maintenance_margin_fraction=new_market_.maintenance_margin_fraction,
            initial_margin_fraction=new_market_.initial_margin_fraction,
            incremental_initial_margin_fraction=new_market_.incremental_initial_margin_fraction,
            incremental_position_size=new_market_.incremental_position_size,
            baseline_position_size=new_market_.baseline_position_size,
            maximum_position_size=new_market_.maximum_position_size
        )
    );

    // Update markets array and mappings
    let (local curr_len) = markets_array_len.read();
    market_id_by_index.write(curr_len, new_market_.id);
    market_index_by_id.write(new_market_.id, curr_len);
    markets_array_len.write(curr_len + 1);
    market_mapping.write(
        asset_id=new_market_.asset, 
        collateral_id=new_market_.assetCollateral, 
        value=new_market_.id
    );

    // Update id & market pair existence
    market_id_exists.write(new_market_.id, TRUE);
    market_pair_exists.write(new_market_.asset, new_market_.assetCollateral, TRUE);

    // Emit event
    market_added.emit(market_id=new_market_.id, market=new_market_);

    return ();
}

// @notice Remove market function
// @param market_id_ - random string generated by zkxnode's mongodb
@external
func remove_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt
) {
    alloc_locals;

    // Verification
    verify_market_manager_authority();
    verify_market_id_exists(market_id_, should_exist_=TRUE);

    // Prepare necessary data
    let (market_to_remove: Market) = market_by_id.read(market_id_);
    let (local index_to_remove) = market_index_by_id.read(market_id_);
    let (local curr_len) = markets_array_len.read();
    local last_market_index = curr_len - 1;
    let (local last_market_id) = market_id_by_index.read(last_market_index);

    with_attr error_message("Markets: Tradable market cannot be removed") {
        assert market_to_remove.is_tradable = FALSE;
    }

    // Replace id_to_remove_ with last_market_id
    market_id_by_index.write(index_to_remove, last_market_id);
    market_index_by_id.write(last_market_id, index_to_remove);

    // Delete id_to_remove_
    market_id_by_index.write(last_market_id, 0);
    markets_array_len.write(curr_len - 1);

    // Mark id & ticker as non-existing
    market_id_exists.write(market_id_, FALSE);
    market_pair_exists.write(market_to_remove.asset, market_to_remove.assetCollateral, FALSE);
    market_mapping.write(
        asset_id=market_to_remove.asset, collateral_id=market_to_remove.assetCollateral, value=0
    );

    // Delete market struct
    market_by_id.write(
        market_id=market_id_, 
        value=Market(
            id=market_id_,
            asset=0, 
            asset_collateral=0, 
            leverage=0, 
            is_tradable=0, 
            is_archived=0, 
            ttl=0,
            tick_size=0,
            step_size=0,
            minimum_order_size=0,
            minimum_leverage=0,
            maximum_leverage=0,
            currently_allowed_leverage=0,
            maintenance_margin_fraction=0,
            initial_margin_fraction=0,
            incremental_initial_margin_fraction=0,
            incremental_position_size=0,
            baseline_position_size=0,
            maximum_position_size=0
        )
    );

    // Emit event
    market_removed.emit(market_id_);

    return ();
}

// @notice Modify leverage for market
// @param market_id_ - string to felt value of selected market
// @param leverage_ - new value for leverage
@external
func modify_leverage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, leverage_: felt
) {
    verify_market_manager_authority();
    verify_market_id_exists(market_id_, should_exist_=TRUE);
    validate_leverage(leverage_);

    let (market: Market) = market_by_id.read(market_id_);

    market_by_id.write(
        market_id=market_id_,
        value=Market(id=market.id,
            asset=market.asset, 
            asset_collateral=market.asset_collateral, 
            leverage=leverage_, 
            is_tradable=market.is_tradable, 
            is_archived=market.is_archived, 
            ttl=market.ttl,
            tick_size=market.tick_size,
            step_size=market.step_size,
            minimum_order_size=market.minimum_order_size,
            minimum_leverage=market.minimum_leverage,
            maximum_leverage=market.maximum_leverage,
            currently_allowed_leverage=market.currently_allowed_leverage,
            maintenance_margin_fraction=market.maintenance_margin_fraction,
            initial_margin_fraction=market.initial_margin_fraction,
            incremental_initial_margin_fraction=market.incremental_initial_margin_fraction,
            incremental_position_size=market.incremental_position_size,
            baseline_position_size=market.baseline_position_size,
            maximum_position_size=market.maximum_position_size
        )
    );

    market_leverage_modified.emit(market_id=market_id_, leverage=leverage_);
    return ();
}

// @notice Modify tradable flag for market
// @param market_id_ - string to felt value of selected market
// @param is_tradable_ - new value for tradable flag
@external
func modify_tradable{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, is_tradable_: felt
) {
    alloc_locals;

    verify_market_manager_authority();
    verify_market_id_exists(market_id_, should_exist_=TRUE);
    with_attr error_message("Markets: is_tradable_ value must be bool") {
        assert_bool(is_tradable_);
    }

    let (market: Market) = market_by_id.read(market_id_);
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset1: Asset) = IAsset.get_asset(contract_address=asset_address, id=market.asset);

    if (is_tradable_ == 2) {
        market_by_id.write(
            market_id=market_id_,
            value=Market(id=market.id,
            asset=market.asset, 
            asset_collateral=market.asset_collateral, 
            leverage=market.leverage, 
            is_tradable=asset1.tradable, 
            is_archived=market.is_archived, 
            ttl=market.ttl,
            tick_size=market.tick_size,
            step_size=market.step_size,
            minimum_order_size=market.minimum_order_size,
            minimum_leverage=market.minimum_leverage,
            maximum_leverage=market.maximum_leverage,
            currently_allowed_leverage=market.currently_allowed_leverage,
            maintenance_margin_fraction=market.maintenance_margin_fraction,
            initial_margin_fraction=market.initial_margin_fraction,
            incremental_initial_margin_fraction=market.incremental_initial_margin_fraction,
            incremental_position_size=market.incremental_position_size,
            baseline_position_size=market.baseline_position_size,
            maximum_position_size=market.maximum_position_size),
        );

        market_tradable_modified.emit(market_id=market_id_, is_tradable=asset1.tradable);
        return ();
    } else {
        if (is_tradable_ == 1) {
            with_attr error_message("Asset 1 is not tradable") {
                assert 1 = 0;
            }
        }
        market_by_id.write(
            market_id=market_id_,
            value=Market(id=market.id,
                asset=market.asset, 
                asset_collateral=market.asset_collateral, 
                leverage=market.leverage, 
                is_tradable=is_tradable_, 
                is_archived=market.is_archived, 
                ttl=market.ttl,
                tick_size=market.tick_size,
                step_size=market.step_size,
                minimum_order_size=market.minimum_order_size,
                minimum_leverage=market.minimum_leverage,
                maximum_leverage=market.maximum_leverage,
                currently_allowed_leverage=market.currently_allowed_leverage,
                maintenance_margin_fraction=market.maintenance_margin_fraction,
                initial_margin_fraction=market.initial_margin_fraction,
                incremental_initial_margin_fraction=market.incremental_initial_margin_fraction,
                incremental_position_size=market.incremental_position_size,
                baseline_position_size=market.baseline_position_size,
                maximum_position_size=market.maximum_position_size
            ),
        );

        market_tradable_modified.emit(market_id=market_id_, is_tradable=is_tradable_);
        return ();
    }
}

// @notice Modify archived state of market
// @param market_id_ - string to felt value of selected market
// @param is_archived_ - new value for archived flag
@external
func modify_archived_state{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, is_archived_: felt
) {
    verify_market_manager_authority();
    verify_market_id_exists(market_id_, should_exist_=TRUE);
    with_attr error_message("Markets: is_archived_ value must be bool") {
        assert_bool(is_archived_);
    }

    let (market: Market) = market_by_id.read(market_id_);

    market_by_id.write(
        market_id=market_id_,
        value=Market(id=market.id,
            asset=market.asset, 
            asset_collateral=market.asset_collateral, 
            leverage=market.leverage, 
            is_tradable=market.is_tradable, 
            is_archived=is_archived_, 
            ttl=market.ttl,
            tick_size=market.tick_size,
            step_size=market.step_size,
            minimum_order_size=market.minimum_order_size,
            minimum_leverage=market.minimum_leverage,
            maximum_leverage=market.maximum_leverage,
            currently_allowed_leverage=market.currently_allowed_leverage,
            maintenance_margin_fraction=market.maintenance_margin_fraction,
            initial_margin_fraction=market.initial_margin_fraction,
            incremental_initial_margin_fraction=market.incremental_initial_margin_fraction,
            incremental_position_size=market.incremental_position_size,
            baseline_position_size=market.baseline_position_size,
            maximum_position_size=market.maximum_position_size
        ),
    );

    market_archived_state_modified.emit(market_id=market_id_, is_archived=is_archived_);

    return ();
}

// @notice Modify trade settings of market 
// @param market_id_ - 
// @param tick_size_ - new tradable flag value for the market
// @param step_size_ - new collateral flag value for the market
// @param minimum_order_size_ - new minimum_order_size value for the market
// @param minimum_leverage_ - new minimum_leverage value for the market
// @param maximum_leverage_ - new maximum_leverage value for the market
// @param currently_allowed_leverage_ - new currently_allowed_leverage value for the market
// @param maintenance_margin_fraction_ - new maintenance_margin_fraction value for the market
// @param initial_margin_fraction_ - new initial_margin_fraction value for the market
// @param incremental_initial_margin_fraction_ - new incremental_initial_margin_fraction value for the market
// @param incremental_position_size_ - new incremental_position_size value for the market
// @param baseline_position_size_ - new baseline_position_size value for the market
// @param maximum_position_size_ - new maximum_position_size value for the market
@external
func modify_trade_settings{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt,
    tick_size_: felt,
    step_size_: felt,
    minimum_order_size_: felt,
    minimum_leverage_: felt,
    maximum_leverage_: felt,
    currently_allowed_leverage_: felt,
    maintenance_margin_fraction_: felt,
    initial_margin_fraction_: felt,
    incremental_initial_margin_fraction_: felt,
    incremental_position_size_: felt,
    baseline_position_size_: felt,
    maximum_position_size_: felt,
) {
    alloc_locals;

    verify_market_manager_authority();
    verify_market_id_exists(market_id_, should_exist_=TRUE);

    let (market: Market) = market_by_id.read(market_id_);
    local updated_market: Market = Market(
        id=market.id,
        asset=market.asset, 
        asset_collateral=market.asset_collateral, 
        leverage=market.leverage, 
        is_tradable=market.is_tradable, 
        is_archived=market.is_archived, 
        ttl=market.ttl,
        tick_size=tick_size_,
        step_size=step_size_,
        minimum_order_size=minimum_order_size_,
        minimum_leverage=minimum_leverage_,
        maximum_leverage=maximum_leverage_,
        currently_allowed_leverage=currently_allowed_leverage_,
        maintenance_margin_fraction=maintenance_margin_fraction_,
        initial_margin_fraction=initial_margin_fraction_,
        incremental_initial_margin_fraction=incremental_initial_margin_fraction_,
        incremental_position_size=incremental_position_size_,
        baseline_position_size=baseline_position_size_,
        maximum_position_size=maximum_position_size_
    );

    // Validate and save updated market
    validate_market_trading_settings(updated_market);
    market_by_id.write(market_id_, updated_market);

    // Emit event
    market_trade_settings_updated.emit(market_id=market_id_, market=market);

    return ();
}

// @notice Modify trade settings of market 
// @param market_id_ - 
// @param tick_size_ - new tradable flag value for the market
// @param step_size_ - new collateral flag value for the market
// @param minimum_order_size_ - new minimum_order_size value for the market
// @param minimum_leverage_ - new minimum_leverage value for the market
// @param maximum_leverage_ - new maximum_leverage value for the market
// @param currently_allowed_leverage_ - new currently_allowed_leverage value for the market
// @param maintenance_margin_fraction_ - new maintenance_margin_fraction value for the market
// @param initial_margin_fraction_ - new initial_margin_fraction value for the market
// @param incremental_initial_margin_fraction_ - new incremental_initial_margin_fraction value for the market
// @param incremental_position_size_ - new incremental_position_size value for the market
// @param baseline_position_size_ - new baseline_position_size value for the market
// @param maximum_position_size_ - new maximum_position_size value for the market
@external
func modify_trade_settings{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt,
    tick_size_: felt,
    step_size_: felt,
    minimum_order_size_: felt,
    minimum_leverage_: felt,
    maximum_leverage_: felt,
    currently_allowed_leverage_: felt,
    maintenance_margin_fraction_: felt,
    initial_margin_fraction_: felt,
    incremental_initial_margin_fraction_: felt,
    incremental_position_size_: felt,
    baseline_position_size_: felt,
    maximum_position_size_: felt,
) {
    alloc_locals;

    verify_market_manager_authority();
    verify_market_id_exists(market_id_, should_exist_=TRUE);

    let (market: Market) = market_by_id.read(market_id=market_id_);

    local updated_market: Market = Market(
        id=market.id,
        asset=market.asset, 
        asset_collateral=market.asset_collateral, 
        leverage=market.leverage, 
        is_tradable=market.is_tradable, 
        is_archived=market.is_archived, 
        ttl=market.ttl,
        tick_size=tick_size_,
        step_size=step_size_,
        minimum_order_size=minimum_order_size_,
        minimum_leverage=minimum_leverage_,
        maximum_leverage=maximum_leverage_,
        currently_allowed_leverage=currently_allowed_leverage_,
        maintenance_margin_fraction=maintenance_margin_fraction_,
        initial_margin_fraction=initial_margin_fraction_,
        incremental_initial_margin_fraction=incremental_initial_margin_fraction_,
        incremental_position_size=incremental_position_size_,
        baseline_position_size=baseline_position_size_,
        maximum_position_size=maximum_position_size_
    );

    // Validate and save updated market
    validate_market_trading_settings(updated_market);
    market_by_id.write(market_id_, updated_market);

    // Emit event
    market_trade_settings_updated.emit(market_id=market_id_, market=market);

    return ();
}

//////////////
// Internal //
//////////////

// @notice Internal Function called by get_all_markets to recursively add assets to the array and return it
// @param iterator - Current index being populated
// @param array_list_len - Stores the current length of the populated array
// @param array_list - Array of Market filled up to the index
// @returns array_list_len - Length of the array_list
// @returns array_list - Fully populated list of Markets
func populate_markets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    iterator: felt, array_list_len: felt, array_list: Market*
) -> (array_list_len: felt, array_list: Market*) {
    alloc_locals;

    if (iterator == array_list_len) {
        return (array_list_len, array_list);
    }

    let (market_id) = market_id_by_index.read(index=iterator);

    let (market_details: Market) = market_by_id.read(market_id=market_id);

    let (id_exists) = market_id_exists.read(market_id);

    if (id_exists == FALSE) {
        return populate_markets(iterator + 1, array_list_len, array_list);
    } else {
        let market_details_w_id = Market(
            id=market_id,
            asset=market_details.asset,
            asset_collateral=market_details.asset_collateral,
            leverage=market_details.leverage,
            is_tradable=market_details.is_tradable,
            is_archived=market_details.is_archived,
            ttl=market_details.ttl,
            tick_size=market_details.tick_size,
            step_size=market_details.step_size,
            minimum_order_size=market_details.minimum_order_size,
            minimum_leverage=market_details.minimum_leverage,
            maximum_leverage=market_details.maximum_leverage,
            currently_allowed_leverage=market_details.currently_allowed_leverage,
            maintenance_margin_fraction=market_details.maintenance_margin_fraction,
            initial_margin_fraction=market_details.initial_margin_fraction,
            incremental_initial_margin_fraction=market_details.incremental_initial_margin_fraction,
            incremental_position_size=market_details.incremental_position_size,
            baseline_position_size=market_details.baseline_position_size,
            maximum_position_size=market_details.maximum_position_size,
        );
        assert array_list[iterator] = market_details_w_id;
        return populate_markets(iterator + 1, array_list_len, array_list);
    }
}

// @notice Internal Function called by get_all_markets to recursively add assets to the array and return it
// @param iterator - Current index being populated
// @param index - It keeps track of element to be added in an array
// @param is_tradable - tradable flag
// @param is_archived - archived flag
// @param array_list_len - Stores the current length of the populated array
// @param array_list - Array of Market filled up to the index
// @returns array_list_len - Length of the array_list
// @returns array_list - Fully populated list of Markets
func populate_markets_by_state{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    iterator: felt,
    index: felt,
    is_tradable: felt,
    is_archived: felt,
    array_list_len: felt,
    array_list: Market*,
) -> (array_list_len: felt, array_list: Market*) {
    alloc_locals;

    if (iterator == array_list_len) {
        return (index, array_list);
    }

    let (market_id) = market_id_by_index.read(index=iterator);

    let (market_details: Market) = market_by_id.read(market_id=market_id);

    let (id_exists) = market_id_exists.read(market_id);
    if (id_exists == FALSE) {
        return populate_markets_by_state(
            iterator + 1, index, is_tradable, is_archived, array_list_len, array_list
        );
    } else {
        if (market_details.is_tradable == is_tradable) {
            if (market_details.is_archived == is_archived) {
                let market_details_w_id = Market(
                    id=market_id,
                    asset=market_details.asset,
                    asset_collateral=market_details.asset_collateral,
                    leverage=market_details.leverage,
                    is_tradable=market_details.is_tradable,
                    is_archived=market_details.is_archived,
                    ttl=market_details.ttl,
                    tick_size=market_details.tick_size,
                    step_size=market_details.step_size,
                    minimum_order_size=market_details.minimum_order_size,
                    minimum_leverage=market_details.minimum_leverage,
                    maximum_leverage=market_details.maximum_leverage,
                    currently_allowed_leverage=market_details.currently_allowed_leverage,
                    maintenance_margin_fraction=market_details.maintenance_margin_fraction,
                    initial_margin_fraction=market_details.initial_margin_fraction,
                    incremental_initial_margin_fraction=market_details.incremental_initial_margin_fraction,
                    incremental_position_size=market_details.incremental_position_size,
                    baseline_position_size=market_details.baseline_position_size,
                    maximum_position_size=market_details.maximum_position_size,
                );
                assert array_list[index] = market_details_w_id;
                return populate_markets_by_state(
                    iterator + 1, index + 1, is_tradable, is_archived, array_list_len, array_list
                );
            }
        }
    }
    return populate_markets_by_state(
        iterator + 1, index, is_tradable, is_archived, array_list_len, array_list
    );
}

// @notice Internal function to check authorization
func verify_market_manager_authority{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}() {
    with_attr error_message("Markets: Caller not authorized to manage markets") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, ManageMarkets_ACTION);
    }
    return ();
}

// @notice Internal function to check if a market exists and returns the required boolean value
// @param market_id - Market id to check for
// @param should_exist - boolean value to assert against
func verify_market_id_exists{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, should_exist_: felt
) {
    with_attr error_message("Markets: market_id existence check failed") {
        let (id_exists) = market_id_exists.read(market_id_);
        assert id_exists = should_exist_;
    }
    return ();
}

// @notice Internal function to validate the leverage value
// @param leverage - Leverage value to validate
func validate_leverage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    leverage_: felt
) {
    with_attr error_message("Markets: Leverage must be in 64x61 format") {
        Math64x61_assert64x61(leverage_);
    }
    with_attr error_message("Markets: Leverage must be >= MIN leverage") {
        assert_le(MIN_LEVERAGE, leverage_);
    }
    with_attr error_message("Markets: Leverage must be <= MAX leverage") {
        let (maximum_leverage) = max_leverage.read();
        assert_le(leverage_, maximum_leverage);
    }
    return ();
}

// @param Internal function to resolve updated market tradable status
// @praram market - struct of type Market
func resolve_tradable_status{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market: Market
) -> (new_tradable: felt) {

    // Get both assets details
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset1: Asset) = IAsset.get_asset(
        contract_address=asset_address, 
        id=market.asset
    );
    let (asset2: Asset) = IAsset.get_asset(
        contract_address=asset_address, 
        id=market.asset_collateral
    );

    // Resolve trading status
    if (market.is_tradable == 2) {
        return (asset1.is_tradable,);
    }
    if (market.is_tradable == 1) {
        with_attr error_message("Markets: Asset 1 tradable cannot be 0 when market tradable is 1") {
            assert asset1.is_tradable = TRUE;
        }
        return (1,);
    }
    return (0,);
}

// @param Internal function to validate market core propeties
// @praram market - struct of type Market
func validate_market_properties{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market: Market
) {
    // Validate Market properties
    with_attr error_message("Markets: market id can't be zero") {
        assert_not_zero(market.id);
    }
    validate_leverage(market.leverage);

    with_attr error_message("Markets: ttl must be in range [1...max_ttl]") {
        let (maximum_ttl) = max_ttl.read();
        assert_le(1, market.ttl);
        assert_le(market.ttl, maximum_ttl);
    }
    with_attr error_message("Markets: is_tradable must be bool") {
        assert_bool(market.is_tradable);
    }
    with_attr error_message("Markets: is_archived must be bool") {
        assert_bool(market.is_archived);
    }

    // Getting both assets details
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset1: Asset) = IAsset.get_asset(
        contract_address=asset_address, 
        id=market.asset
    );
    let (asset2: Asset) = IAsset.get_asset(
        contract_address=asset_address, 
        id=market.assetCollateral
    );

    // Verify assets exist and validate collateral's status
    with_attr error_message("Markets: Asset 1 is not registred as an asset") {
        assert_not_zero(asset1.id);
    }
    with_attr error_message("Asset 2 is not registred as an asset") {
        assert_not_zero(asset2.id);
    }
    with_attr error_message("Asset 2 is not a collateral") {
        assert asset2.is_collateral = TRUE;
    }
    return ();
}

// @param Internal function to validate market trading propeties
// @praram market - struct of type Market
func validate_market_trading_settings{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_: Market
) {
    with_attr error_message("Markets: Invalid trade settings") {
        Math64x61_assertPositive64x61(market_.tick_size);
        Math64x61_assertPositive64x61(market_.step_size);
        Math64x61_assertPositive64x61(market_.minimum_order_size);
        Math64x61_assertPositive64x61(market_.maintenance_margin_fraction);
        Math64x61_assertPositive64x61(market_.initial_margin_fraction);
        Math64x61_assertPositive64x61(market_.incremental_initial_margin_fraction);
    }
    with_attr error_message("Markets: Invalid min leverage") {
        Math64x61_assertPositive64x61(market_.minimum_leverage);
    }
    with_attr error_message("Markets: Invalid max leverage") {
        Math64x61_assertPositive64x61(market_.maximum_leverage);
        assert_le(market_.minimum_leverage, market_.maximum_leverage);
    }
    with_attr error_message("Markets: Invalid currently allowed leverage") {
        Math64x61_assertPositive64x61(market_.currently_allowed_leverage);
        assert_le(market_.minimum_leverage, market_.currently_allowed_leverage);
        assert_le(market_.currently_allowed_leverage, market_.maximum_leverage);
    }
    with_attr error_message("Markets: Invalid position size settings") {
        Math64x61_assertPositive64x61(market_.incremental_position_size);
        Math64x61_assertPositive64x61(market_.baseline_position_size);
        Math64x61_assertPositive64x61(market_.maximum_position_size);
        assert_le(market_.baseline_position_size, market_.maximum_position_size);
    }
    return ();
}
