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
from contracts.Math_64x61 import Math64x61_assert64x61

//############
// Constants #
//############
const MAX_TRADABLE = 2;
const MIN_LEVERAGE = 2305843009213693952;

//#########
// Events #
//#########

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
func market_tradable_modified(market_id: felt, is_tradable: felt) {
}

// Event emitted whenever a market's archived parameter is modified
@event
func market_archived_state_modified(market_id: felt, is_archived: felt) {
}

//##########
// Storage #
//##########

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
func market_pair_exists(asset: felt, asset_collateral: felt) -> (res: felt) {
}

//##############
// Constructor #
//##############

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    max_leverage.write(23058430092136939520);
    max_ttl.write(3600);
    return ();
}

//#################
// View Functions #
//#################

// @notice View function to return all the markets with ids in an array
// @returns array_list_len - Length of the array_list
// @returns array_list - Fully populated list of Markets
@view
func get_all_markets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    array_list_len: felt, array_list: Market*
) {
    alloc_locals;

    let (array_list: Market*) = alloc();
    let (array_list_len) = markets_array_len.read();
    return populate_markets(iterator=0, array_list_len=array_list_len, array_list=array_list);
}

// @notice Getter function for Markets
// @param id - random string generated by zkxnode's mongodb
// @return currMarket - Returns the requested market
@view
func get_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(id_: felt) -> (
    currMarket: Market
) {
    let (currMarket) = market_by_id.read(market_id=id_);
    return (currMarket,);
}

// @notice Getter function for Markets from assetID and collateralID
// @param assetID - Id of the asset
// @param collateralID - Id of the collateral
// @return currMarket - Returns the requested market
@view
func get_market_from_assets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, collateral_id_: felt
) -> (market_id: felt) {
    let (currMarket) = market_mapping.read(asset_id=asset_id_, collateral_id=collateral_id_);
    return (currMarket,);
}

// @notice Getter function to get collateral asset from market_id
// @param market_id - Market Id
// @returns collateral_id - Collateral Id of the market
@view
func get_collateral_from_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id: felt
) -> (collateral_id: felt) {
    let (currMarket) = market_by_id.read(market_id=market_id);
    return (currMarket.assetCollateral,);
}

// @notice Getter function to get asset & collateral pair from market_id
// @param market_id - Market Id
// @returns asset_id - Asset Id of the market
// @returns collateral_id - Collateral Id of the market
@view
func get_asset_collateral_from_market{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(market_id: felt) -> (asset_id: felt, collateral_id: felt) {
    let (currMarket) = market_by_id.read(market_id=market_id);
    return (currMarket.asset, currMarket.assetCollateral);
}

// @notice Getter function to get ttl of a market
// @param market_id - Market Id
// @returns ttl - ttl of the market
@view
func get_ttl_from_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id: felt
) -> (ttl: felt) {
    let (currMarket) = market_by_id.read(market_id=market_id);
    return (currMarket.ttl,);
}

// @notice View function to return markets by their state with ids in an array
// @param tradable - tradable flag
// @param archived - archived flag
// @returns array_list_len - Length of the array_list
// @returns array_list - Fully populated list of Market
@view
func get_markets_by_state{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tradable_: felt, archived_: felt
) -> (array_list_len: felt, array_list: Market*) {
    alloc_locals;

    let (array_list: Market*) = alloc();
    let (array_list_len) = markets_array_len.read();
    return populate_markets_by_state(
        iterator=0,
        index=0,
        is_tradable=tradable_,
        is_archived=archived_,
        array_list_len=array_list_len,
        array_list=array_list,
    );
}

//#####################
// External Functions #
//#####################

// @notice Function called by admin to change the max leverage allowed in the system
// @param new_max_leverage - New maximmum leverage
@external
func change_max_leverage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_max_leverage_: felt
) {
    verify_caller_authority_market();

    with_attr error_message("Max leverage should be more than or equal to 1") {
        assert_le(1, new_max_leverage_);
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
    verify_caller_authority_market();

    with_attr error_message("Max ttl cannot be 0") {
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

    // Auth Check
    assert_not_zero(new_market_.id);
    verify_caller_authority_market();
    verify_market_id_exists(new_market_.id, should_exist_=FALSE);
    verify_market_pair_exists(new_market_.asset, new_market_.asset_collateral, should_exist_=FALSE);
    let (new_tradable) = validate_market_properties(new_market_);

    market_by_id.write(
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
        maximum_position_size=new_market_.maximum_position_size)
    );

    // Save it to storage
    let (curr_len) = markets_array_len.read();
    market_id_by_index.write(curr_len, new_market_.id);
    market_index_by_id.write(new_market_.id, curr_len);
    markets_array_len.write(curr_len + 1);
    market_mapping.write(
        asset_id=new_market_.asset, collateral_id=new_market_.asset_collateral, value=new_market_.id
    );

    // Update id & market pair existence
    market_id_exists.write(new_market_.id, TRUE);
    market_pair_exists.write(new_market_.asset, new_market_.asset_collateral, TRUE);

    // Save new_market_ struct
    market_by_id.write(market_id=new_market_.id, value=new_market_);

    market_added.emit(market_id=new_market_.id, market=new_market_);
    return ();
}

// @notice Remove market function
// @param id - random string generated by zkxnode's mongodb
@external
func remove_market{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id_to_remove_: felt
) {
    alloc_locals;

    // Auth Check
    verify_caller_authority_market();
    verify_market_id_exists(id_to_remove_, should_exist_=TRUE);

    // Prepare necessary data
    let (market_to_remove: Market) = market_by_id.read(market_id=id_to_remove_);
    let (local index_to_remove) = market_index_by_id.read(id_to_remove_);
    let (local curr_len) = markets_array_len.read();
    local last_market_index = curr_len - 1;
    let (local last_market_id) = market_id_by_index.read(last_market_index);

    with_attr error_message("Tradable market cannot be removed") {
        assert_le(market_to_remove.is_tradable, 0);
    }

    // Replace id_to_remove_ with last_market_id
    market_id_by_index.write(index_to_remove, last_market_id);
    market_index_by_id.write(last_market_id, index_to_remove);

    // Delete id_to_remove_
    market_id_by_index.write(last_market_id, 0);
    markets_array_len.write(curr_len - 1);

    // Mark id & ticker as non-existing
    market_id_exists.write(id_to_remove_, FALSE);
    market_pair_exists.write(market_to_remove.asset, market_to_remove.asset_collateral, FALSE);
    market_mapping.write(
        asset_id=market_to_remove.asset, collateral_id=market_to_remove.asset_collateral, value=0
    );

    // Delete market struct
    market_by_id.write(
        market_id=id_to_remove_,
        value=Market(id=id_to_remove_,
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
        maximum_position_size=0),
    );

    market_removed.emit(market_id=id_to_remove_);
    return ();
}

// @notice Modify leverage for market
// @param id - random string generated by zkxnode's mongodb
// @param leverage - new value for leverage
@external
func modify_leverage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id_: felt, leverage_: felt
) {
    verify_caller_authority_market();
    verify_market_id_exists(id_, should_exist_=TRUE);
    verify_leverage(leverage_);

    let (market: Market) = market_by_id.read(market_id=id_);

    market_by_id.write(
        market_id=id_,
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
        maximum_position_size=market.maximum_position_size),
    );

    market_leverage_modified.emit(market_id=id_, leverage=leverage_);
    return ();
}

// @notice Modify tradable flag for market
// @param id_ - random string generated by zkxnode's mongodb
// @param is_tradable_ - new value for tradable flag
@external
func modify_tradable{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id_: felt, is_tradable_: felt
) {
    alloc_locals;
    // Auth Check
    verify_caller_authority_market();
    verify_market_id_exists(id_, should_exist_=TRUE);
    verify_tradable(is_tradable_);

    let (market: Market) = market_by_id.read(market_id=id_);

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset1: Asset) = IAsset.get_asset(contract_address=asset_address, id=market.asset);

    if (is_tradable_ == 2) {
        market_by_id.write(
            market_id=id_,
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

        market_tradable_modified.emit(market_id=id_, is_tradable=asset1.tradable);
        return ();
    } else {
        if (is_tradable_ == 1) {
            with_attr error_message("Asset 1 is not tradable") {
                assert_not_zero(asset1.tradable);
            }
        }
        market_by_id.write(
            market_id=id_,
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
            maximum_position_size=market.maximum_position_size),
        );

        market_tradable_modified.emit(market_id=id_, is_tradable=is_tradable_);
        return ();
    }
}

// @notice Modify archived state of market
// @param id_ - random string generated by zkxnode's mongodb
// @param is_archived_ - new value for archived flag
@external
func modify_archived_state{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id_: felt, is_archived_: felt
) {
    verify_caller_authority_market();
    verify_market_id_exists(id_, should_exist_=TRUE);
    verify_archived(is_archived_);

    let (market: Market) = market_by_id.read(market_id=id_);

    market_by_id.write(
        market_id=id_,
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
        maximum_position_size=market.maximum_position_size),
    );

    market_archived_state_modified.emit(market_id=id_, is_archived=is_archived_);
    return ();
}

//#####################
// Internal Functions #
//#####################

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
func verify_caller_authority_market{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}() {
    with_attr error_message("Caller not authorized to manage markets") {
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
    with_attr error_message("market_id existence mismatch") {
        let (id_exists) = market_id_exists.read(market_id_);
        assert id_exists = should_exist_;
    }
    return ();
}

// @notice Internal function to check if a market pair exists and returns the required boolean value
// @param asset - Asset of the market pair
// @param asset_collateral - Collateral of the market pair
// @param should_exist - boolean value to assert against
func verify_market_pair_exists{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_: felt, asset_collateral_: felt, should_exist_: felt
) {
    with_attr error_message("Market pair existence mismatch") {
        let (pair_exists) = market_pair_exists.read(asset_, asset_collateral_);
        assert pair_exists = should_exist_;
    }
    return ();
}

// @notice Internal function to verify the leverage value
// @param leverage - Leverage value to verify
func verify_leverage{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    leverage_: felt
) {
    with_attr error_message("Leverage should be in 64x61 format") {
        Math64x61_assert64x61(leverage_);
    }

    with_attr error_message("Leverage should be more than or equal to 1") {
        assert_le(MIN_LEVERAGE, leverage_);
    }

    let (maximum_leverage) = max_leverage.read();
    with_attr error_message("Leverage should be less than or equal to max leverage") {
        assert_le(leverage_, maximum_leverage);
    }

    return ();
}

// @notice Internal function to verify the ttl value
// @param ttl - ttl value to verify
func verify_ttl{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(ttl_: felt) {
    with_attr error_message("ttl cannot be less than 1") {
        assert_le(1, ttl_);
    }

    let (maximum_ttl) = max_ttl.read();
    with_attr error_message("ttl should be less than or equal to max ttl") {
        assert_le(ttl_, maximum_ttl);
    }

    return ();
}

// @param Internal function to verify the tradable value
// @praram tradable - tradable value to verify
func verify_tradable{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    tradable_: felt
) {
    with_attr error_message("Tradable cannot be less than zero") {
        assert_le(0, tradable_);
    }

    with_attr error_message("Tradable should be less than or equal to max trabele") {
        assert_le(tradable_, MAX_TRADABLE);
    }

    return ();
}

// @param Internal function to verify archived value
// @praram archived - archived value to verify
func verify_archived{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    archived_: felt
) {
    with_attr error_message("Archived value can be either 0 or 1") {
        assert_nn(archived_);
        assert_le(archived_, 1);
    }

    return ();
}

// @param Internal function to verify the market propeties b
// @praram market - struct of type Market
func validate_market_properties{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market: Market
) -> (newTradable: felt) {
    verify_leverage(market.leverage);
    verify_ttl(market.ttl);
    verify_tradable(market.is_tradable);

    // Getting asset details
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset1: Asset) = IAsset.get_asset(contract_address=asset_address, id=market.asset);
    let (asset2: Asset) = IAsset.get_asset(
        contract_address=asset_address, id=market.asset_collateral
    );

    with_attr error_message("Asset 2 is not a collateral") {
        assert_not_zero(asset2.collateral);
    }

    with_attr error_message("Asset 1 is not registred as an asset") {
        assert_not_zero(asset1.ticker);
    }

    if (market.is_tradable == 2) {
        return (asset1.tradable,);
    } else {
        if (market.is_tradable == 1) {
            with_attr error_message("Asset 1 tradable cannot be 0 when market tradable is 1") {
                assert_not_zero(asset1.tradable);
            }
            return (1,);
        } else {
            return (0,);
        }
    }
}
