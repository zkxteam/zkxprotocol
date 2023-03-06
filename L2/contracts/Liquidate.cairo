%lang starknet

from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math_cmp import is_le

from contracts.Constants import Asset_INDEX, LONG, Market_INDEX
from contracts.DataTypes import (
    Asset,
    LiquidatablePosition,
    MultipleOrder,
    PositionDetailsForRiskManagement,
)
from contracts.interfaces.IAccountManager import IAccountManager
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IMarkets import IMarkets
from contracts.libraries.CommonLibrary import CommonLib
from contracts.Math_64x61 import (
    Math64x61_div,
    Math64x61_is_le,
    Math64x61_mul,
    Math64x61_add,
    Math64x61_sub,
    Math64x61_round,
)

// ///////////////
// Test Helpers //
// ///////////////

@storage_var
func maintenance() -> (maintenance: felt) {
}

@storage_var
func acc_value() -> (acc_value: felt) {
}

// /////////////////
// View functions //
// /////////////////

// @notice Function to return maintenance requirement of last called collateral_id of a user
@view
func return_maintenance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (_maintenance) = maintenance.read();
    return (res=_maintenance);
}

// @notice Function to return account value of last called collateral_id of a user
@view
func return_acc_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (_acc_value) = acc_value.read();
    return (res=_acc_value);
}

// /////////
// Events //
// /////////

// Event emitted whenever mark_under_collateralized_position() is called
@event
func mark_under_collateralized_position_called(
    account_address: felt,
    liq_result: felt,
    least_collateral_ratio_position: PositionDetailsForRiskManagement,
) {
}

// Event emitted whenever check_for_risk() is called
@event
func can_order_be_opened(order: MultipleOrder) {
}

// Event emitted whenever position can be deleveraged
@event
func position_to_be_deleveraged(
    position: PositionDetailsForRiskManagement, amount_to_be_sold: felt
) {
}

// //////////////
// Constructor //
// //////////////

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    return ();
}

// ///////////
// External //
// ///////////

// @notice Function to find and mark the positions to be liquidated/deleveraged
// @param account_address_ - Account address of the user
// @param collateral_id_ - Collateral Id of the isolated cross-margin order_value_with_fee
// @return liq_result_ - 1 if to be liq/del,
// @return least_collateral_ratio_position - Position which has the least collateral ratio
// @return total_account_value - Total account value of the positions for the corresponding collateral
// @return total_maintenance_requirement - Total maintenece requirement of the positions for the corresponding collateral
@external
func mark_under_collateralized_position{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(account_address_: felt, collateral_id_: felt) -> (
    liq_result: felt,
    least_collateral_ratio_position: PositionDetailsForRiskManagement,
    total_account_value: felt,
    total_maintenance_requirement: felt,
) {
    alloc_locals;

    let (
        liquidatable_position: LiquidatablePosition
    ) = IAccountManager.get_deleveragable_or_liquidatable_position(
        contract_address=account_address_, collateral_id_=collateral_id_
    );

    if (liquidatable_position.amount_to_be_sold != 0) {
        return (TRUE, PositionDetailsForRiskManagement(0, 0, 0, 0, 0, 0, 0), 0, 0);
    }

    let (
        liq_result: felt,
        total_margin: felt,
        available_margin: felt,
        unrealized_pnl_sum: felt,
        maintenance_margin_requirement: felt,
        least_collateral_ratio: felt,
        least_collateral_ratio_position: PositionDetailsForRiskManagement,
        least_collateral_ratio_position_asset_price: felt,
    ) = IAccountManager.get_margin_info(
        contract_address=account_address_,
        asset_id_=collateral_id_,
        new_position_maintanence_requirement_=0,
        new_position_margin_=0,
    );

    if (least_collateral_ratio_position_asset_price == 0) {
        return (FALSE, PositionDetailsForRiskManagement(0, 0, 0, 0, 0, 0, 0), 0, 0);
    }

    // /////////////////
    // TO BE REMOVED //
    maintenance.write(maintenance_margin_requirement);
    acc_value.write(total_margin);
    // /////////////////

    // Get Market contract address
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (local market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    if (liq_result == TRUE) {
        // if margin ratio is <=0, we directly perform liquidation else we check for deleveraging
        if (is_le(least_collateral_ratio, 0) == FALSE) {
            let (amount_to_be_sold) = check_deleveraging(
                market_address_=market_address,
                position_=least_collateral_ratio_position,
                asset_price_=least_collateral_ratio_position_asset_price,
            );
            IAccountManager.liquidate_position(
                contract_address=account_address_,
                collateral_id_=collateral_id_,
                position_=least_collateral_ratio_position,
                amount_to_be_sold_=amount_to_be_sold,
            );
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            IAccountManager.liquidate_position(
                contract_address=account_address_,
                collateral_id_=collateral_id_,
                position_=least_collateral_ratio_position,
                amount_to_be_sold_=0,
            );
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // mark_under_collateralized_position_called event is emitted
    mark_under_collateralized_position_called.emit(
        account_address=account_address_,
        liq_result=liq_result,
        least_collateral_ratio_position=least_collateral_ratio_position,
    );

    return (
        liq_result,
        least_collateral_ratio_position,
        available_margin,
        maintenance_margin_requirement,
    );
}

// @notice Function to check if position can be opened
// @param order - MultipleOrder structure
// @param size - matched order size of current order
// @param execution_price - Execution price of current order
@external
func check_for_risk{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_: MultipleOrder, size_: felt, execution_price_: felt, margin_amount_: felt
) -> (available_margin: felt) {
    alloc_locals;

    can_order_be_opened.emit(order=order_);

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get required contract addresses from the AuthorizedRegistry
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get the asset ID and collateral ID of the position
    let (asset_id: felt, collateral_id: felt) = IMarkets.get_asset_collateral_from_market(
        contract_address=market_address, market_id_=order_.market_id
    );

    // Fetch the maintanence margin requirement from Markets contract
    let (req_margin) = IMarkets.get_maintenance_margin(
        contract_address=market_address, market_id_=order_.market_id
    );

    // Calculate needed values
    let (leveraged_position_value) = Math64x61_mul(execution_price_, size_);
    let (maintenance_requirement) = Math64x61_mul(req_margin, leveraged_position_value);

    // Recurse through all positions to see if it needs to liquidated
    let (
        is_liquidation: felt,
        total_margin: felt,
        available_margin: felt,
        unrealized_pnl_sum: felt,
        maintenance_margin_requirement: felt,
        least_collateral_ratio: felt,
        least_collateral_ratio_position: PositionDetailsForRiskManagement,
        least_collateral_ratio_position_asset_price: felt,
    ) = IAccountManager.get_margin_info(
        contract_address=order_.user_address,
        asset_id_=collateral_id,
        new_position_maintanence_requirement_=maintenance_requirement,
        new_position_margin_=margin_amount_,
    );

    local order_id;
    local market_id;
    assert order_id = order_.order_id;
    assert market_id = order_.market_id;
    with_attr error_message("1101: {order_id} {market_id}") {
        assert is_liquidation = FALSE;
    }
    return (available_margin,);
}

// ////////////
// Internal //
// ////////////

// @notice Function to calculate amount to be put on sale for deleveraging
// @param market_address_ - Address of the Market contract
// @param position_ - position to be deleveraged
// @param asset_price_ - asset price of the asset in the position
// @return amount_to_sold - amount to be put on sale for deleveraging
func check_deleveraging{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_address_: felt, position_: PositionDetailsForRiskManagement, asset_price_: felt
) -> (amount_to_be_sold: felt) {
    alloc_locals;
    // Read the registry and version
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get Asset contract address
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );

    // Get Market contract address
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Fetch the maintatanence margin requirement from Markets contract
    let (req_margin) = IMarkets.get_maintenance_margin(
        contract_address=market_address_, market_id_=position_.market_id
    );

    let margin_amount = position_.margin_amount;
    let borrowed_amount = position_.borrowed_amount;
    let position_size = position_.position_size;

    local price_diff;
    if (position_.direction == LONG) {
        let (diff) = Math64x61_sub(asset_price_, position_.avg_execution_price);
        price_diff = diff;
    } else {
        let (diff) = Math64x61_sub(position_.avg_execution_price, asset_price_);
        price_diff = diff;
    }

    // get collateral id
    let (asset_id: felt, collateral_id: felt) = IMarkets.get_asset_collateral_from_market(
        contract_address=market_address, market_id_=position_.market_id
    );

    // Get Asset to fetch number of token decimals of an asset
    let (asset: Asset) = IAsset.get_asset(contract_address=asset_address, id=asset_id);

    // Calculate amount to be sold for deleveraging
    let (maintenance_requirement) = Math64x61_mul(req_margin, asset_price_);
    let (price_diff_maintenance) = Math64x61_sub(maintenance_requirement, price_diff);
    let (amount_to_be_present) = Math64x61_div(margin_amount, price_diff_maintenance);
    let (amount_to_be_sold_not_rounded) = Math64x61_sub(position_size, amount_to_be_present);
    let (amount_to_be_sold) = Math64x61_round(amount_to_be_sold_not_rounded, asset.token_decimal);

    // Calculate the leverage after deleveraging
    let (position_value) = Math64x61_add(margin_amount, borrowed_amount);
    let (amount_to_be_sold_value) = Math64x61_mul(amount_to_be_sold, position_.avg_execution_price);
    let (remaining_position_value) = Math64x61_sub(position_value, amount_to_be_sold_value);
    let (leverage_after_deleveraging) = Math64x61_div(remaining_position_value, margin_amount);

    // to64x61(2) == 4611686018427387904
    let (can_be_liquidated) = Math64x61_is_le(leverage_after_deleveraging, 4611686018427387904, 5);
    if (can_be_liquidated == TRUE) {
        return (FALSE,);
    } else {
        // position_to_be_deleveraged event is emitted
        position_to_be_deleveraged.emit(position=position_, amount_to_be_sold=amount_to_be_sold);
        return (amount_to_be_sold,);
    }
}
