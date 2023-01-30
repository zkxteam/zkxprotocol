%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.math import assert_nn, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address

from contracts.Constants import (
    Asset_INDEX,
    CollateralPrices_INDEX,
    LONG,
    Market_INDEX,
    MarketPrices_INDEX,
)
from contracts.DataTypes import (
    CollateralBalance,
    CollateralPrice,
    Market,
    MarketPrice,
    MultipleOrder,
    PriceData,
    PositionDetails,
    PositionDetailsForRiskManagement,
)
from contracts.interfaces.IAccountManager import IAccountManager
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IMarkets import IMarkets
from contracts.interfaces.IMarketPrices import IMarketPrices
from contracts.libraries.CommonLibrary import CommonLib
from contracts.Math_64x61 import (
    Math64x61_div,
    Math64x61_mul,
    Math64x61_add,
    Math64x61_sub,
    Math64x61_ONE,
)

// ////////////////
// Test Helpers //
// ////////////////

@storage_var
func maintenance() -> (maintenance: felt) {
}

@storage_var
func acc_value() -> (acc_value: felt) {
}

@view
func return_maintenance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (_maintenance) = maintenance.read();
    return (res=_maintenance);
}

@view
func return_acc_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (_acc_value) = acc_value.read();
    return (res=_acc_value);
}

// //////////
// Events //
// //////////

// Event emitted whenever find_under_collateralized_position() is called
@event
func find_under_collateralized_position_called(
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

// ///////////////
// Constructor //
// ///////////////

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

// ////////////
// External //
// ////////////

// @notice Function to check and mark the positions to be liquidated
// @param account_address - Account address of the user
// @param prices_len - Length of the prices array
// @param prices - Array with all the price details
// @return res - 1 if positions are marked to be liquidated
@external
func find_under_collateralized_position{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(account_address_: felt, collateral_id_: felt) -> (
    liq_result: felt,
    least_collateral_ratio_position: PositionDetailsForRiskManagement,
    total_account_value: felt,
    total_maintenance_requirement: felt,
) {
    alloc_locals;
    // Check if the caller is a node

    // Fetch all the positions from the Account contract
    let (
        positions_len: felt, positions: PositionDetailsForRiskManagement*
    ) = IAccountManager.get_positions_for_risk_management(
        contract_address=account_address_, collateral_id_=collateral_id_
    );

    // Check if the list is empty
    with_attr error_message("Liquidate: User's positions array is empty") {
        assert_not_zero(positions_len);
    }

    // Get Market contract address
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (local market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    let (local market_price_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=MarketPrices_INDEX, version=version
    );

    // Recurse through all positions to see if it needs to liquidated
    let (
        liq_result,
        least_collateral_ratio,
        least_collateral_ratio_position,
        least_collateral_ratio_position_asset_price,
        total_account_value,
        total_maintenance_requirement,
    ) = check_liquidation_recurse(
        account_address_=account_address_,
        market_address_=market_address,
        market_price_address_=market_price_address,
        positions_len_=positions_len,
        positions_=positions,
        collateral_id_=collateral_id_,
        total_account_value_=0,
        total_maintenance_requirement_=0,
        least_collateral_ratio_=Math64x61_ONE,
        least_collateral_ratio_position_=PositionDetailsForRiskManagement(0, 0, 0, 0, 0, 0, 0),
        least_collateral_ratio_position_asset_price_=0,
    );

    if (liq_result == TRUE) {
        // if margin ratio is <=0, we directly perform liquidation else we check for deleveraging
        if (is_le(least_collateral_ratio, 0) == FALSE) {
            let (amount_to_be_sold) = check_deleveraging(
                account_address_=account_address_,
                market_address_=market_address,
                position_=least_collateral_ratio_position,
                asset_price_=least_collateral_ratio_position_asset_price,
            );
            IAccountManager.liquidate_position(
                contract_address=account_address_,
                position_=least_collateral_ratio_position,
                amount_to_be_sold_=amount_to_be_sold,
            );
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            IAccountManager.liquidate_position(
                contract_address=account_address_,
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

    // find_under_collateralized_position_called event is emitted
    find_under_collateralized_position_called.emit(
        account_address=account_address_,
        liq_result=liq_result,
        least_collateral_ratio_position=least_collateral_ratio_position,
    );

    return (
        liq_result,
        least_collateral_ratio_position,
        total_account_value,
        total_maintenance_requirement,
    );
}

// @notice Function to check if position can be opened
// @param order - MultipleOrder structure
// @param size - matched order size of current order
// @param execution_price - Execution price of current order
@external
func check_for_risk{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order: MultipleOrder, size: felt, execution_price: felt
) {
    alloc_locals;

    can_order_be_opened.emit(order=order);

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get required contract addresses from the AuthorizedRegistry
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    let (market_price_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=MarketPrices_INDEX, version=version
    );

    // Get the asset ID and collateral ID of the position
    let (asset_id: felt, collateral_id: felt) = IMarkets.get_asset_collateral_from_market(
        contract_address=market_address, market_id_=order.market_id
    );

    // Get a list with all positions with the same collateral from AccountManager contract
    let (
        positions_len: felt, positions: PositionDetailsForRiskManagement*
    ) = IAccountManager.get_positions_for_risk_management(
        contract_address=order.user_address, collateral_id_=collateral_id
    );

    // Fetch the maintanence margin requirement from Markets contract
    let (req_margin) = IMarkets.get_maintenance_margin(
        contract_address=market_address, market_id_=order.market_id
    );

    // Calculate needed values
    let (leveraged_position_value) = Math64x61_mul(execution_price, size);

    let (total_position_value) = Math64x61_div(leveraged_position_value, order.leverage);
    let (amount_to_be_borrowed) = Math64x61_sub(leveraged_position_value, total_position_value);

    let (account_value) = Math64x61_sub(leveraged_position_value, amount_to_be_borrowed);
    let (maintenance_requirement) = Math64x61_mul(req_margin, leveraged_position_value);

    // Recurse through all positions to see if it needs to liquidated
    let (
        liq_result,
        least_collateral_ratio,
        least_collateral_ratio_position,
        least_collateral_ratio_position_asset_price,
        total_account_value,
        total_maintenance_requirement,
    ) = check_liquidation_recurse(
        account_address_=order.user_address,
        market_address_=market_address,
        market_price_address_=market_price_address,
        positions_len_=positions_len,
        positions_=positions,
        collateral_id_=collateral_id,
        total_account_value_=account_value,
        total_maintenance_requirement_=maintenance_requirement,
        least_collateral_ratio_=Math64x61_ONE,
        least_collateral_ratio_position_=PositionDetailsForRiskManagement(0, 0, 0, 0, 0, 0, 0),
        least_collateral_ratio_position_asset_price_=0,
    );

    local order_id;
    local market_id;
    assert order_id = order.order_id;
    assert market_id = order.market_id;
    with_attr error_message("1101: {order_id} {market_id}") {
        assert liq_result = FALSE;
    }
    return ();
}

// ////////////
// Internal //
// ////////////

// @notice Function that is called recursively by check_recurse
// @param account_address_ - Account address of the user
// @param market_address_ - Markets contarct address
// @param positions_len_ - Length of the positions_ array
// @param postions_ - Array with all the position details
// @param prices_array_ - Array with all the price details
// @param total_account_value_ - Collateral value - borrowed value + positionSize * price
// @param total_maintenance_requirement_ - maintenance ratio of the asset * value of the position when executed
// @param least_collateral_ratio_ - The least collateral ratio among the positions
// @param least_collateral_ratio_position_ - The position which is having the least collateral ratio
// @param least_collateral_ratio_position_collateral_price_ - Collateral price of the collateral in the postion which is having the least collateral ratio
// @param least_collateral_ratio_position_asset_price_ - Asset price of an asset in the postion which is having the least collateral ratio
// @return is_liquidation - 1 if positions are marked to be liquidated
// @return least_collateral_ratio_ - least collateral ratio
// @return least_collateral_ratio_position_ - The least collateralized position
// @return least_collateral_ratio_position_asset_price_ - Asset price of an asset in least_collateral_ratio_position
func check_liquidation_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_address_: felt,
    market_address_: felt,
    market_price_address_: felt,
    positions_len_: felt,
    positions_: PositionDetailsForRiskManagement*,
    collateral_id_: felt,
    total_account_value_: felt,
    total_maintenance_requirement_: felt,
    least_collateral_ratio_: felt,
    least_collateral_ratio_position_: PositionDetailsForRiskManagement,
    least_collateral_ratio_position_asset_price_: felt,
) -> (
    is_liquidation: felt,
    least_collateral_ratio: felt,
    least_collateral_ratio_position: PositionDetailsForRiskManagement,
    least_collateral_ratio_position_asset_price: felt,
    total_account_value: felt,
    total_maintenance_requirement: felt,
) {
    alloc_locals;

    // Check if the list is empty, if yes return the result
    if (positions_len_ == 0) {
        // Fetch all the collaterals that the user holds
        let (user_balance: felt) = IAccountManager.get_balance(
            contract_address=account_address_, assetID_=collateral_id_
        );

        // Add the collateral value to the total_account_value_
        local total_account_value_collateral = total_account_value_ + user_balance;

        // /////////////////
        // TO BE REMOVED //
        maintenance.write(total_maintenance_requirement_);
        acc_value.write(total_account_value_collateral);
        // /////////////////

        // Check if the maintenance margin is not satisfied
        let is_liquidation = is_le(total_account_value_collateral, total_maintenance_requirement_);

        // Return if the account should be liquidated or not and the orderId of the least colalteralized position
        return (
            is_liquidation,
            least_collateral_ratio_,
            least_collateral_ratio_position_,
            least_collateral_ratio_position_asset_price_,
            total_account_value_collateral,
            total_maintenance_requirement_,
        );
    }

    let (market_price: MarketPrice) = IMarketPrices.get_market_price(
        contract_address=market_address_, id=[positions_].market_id
    );

    // Get the market ttl from the market contract
    let (market_ttl: felt) = IMarkets.get_ttl_from_market(
        contract_address=market_address_, market_id_=[positions_].market_id
    );

    // Calculate the timestamp
    let (current_timestamp) = get_block_timestamp();
    tempvar ttl = market_ttl;
    tempvar timestamp = market_price.timestamp;
    tempvar time_difference = current_timestamp - timestamp;

    // ttl has passed, return 0
    let status = is_le(time_difference, ttl);
    if (status == FALSE) {
        return (0, 0, PositionDetailsForRiskManagement(0, 0, 0, 0, 0, 0, 0), 0, 0, 0);
    }

    let (req_margin) = IMarkets.get_maintenance_margin(
        contract_address=market_address_, market_id_=[positions_].market_id
    );

    // Calculate the required margin
    let (maintenance_position) = Math64x61_mul(
        [positions_].avg_execution_price, [positions_].position_size
    );
    let (maintenance_requirement) = Math64x61_mul(req_margin, maintenance_position);

    // Calculate pnl to check if it is the least collateralized position
    local test_;
    local price_diff_;
    if ([positions_].direction == 1) {
        tempvar price_diff = market_price.price - [positions_].avg_execution_price;
        price_diff_ = price_diff;
        test_ = 0;
    } else {
        tempvar price_diff = [positions_].avg_execution_price - market_price.price;
        price_diff_ = price_diff;
        test_ = price_diff;
    }

    let (pnl) = Math64x61_mul(price_diff_, [positions_].position_size);

    // Calculate the value of the current account margin
    let (position_value_wo_pnl: felt) = Math64x61_sub(
        maintenance_position, [positions_].borrowed_amount
    );

    let (position_value: felt) = Math64x61_add(position_value_wo_pnl, pnl);

    // Margin ratio calculation
    local numerator = [positions_].margin_amount + pnl;
    let (denominator) = Math64x61_mul([positions_].position_size, market_price.price);
    let (collateral_ratio_position) = Math64x61_div(numerator, denominator);

    let is_lesser = is_le(collateral_ratio_position, least_collateral_ratio_);

    // If it is the lowest, update least_collateral_ratio and least_collateral_ratio_position
    local least_collateral_ratio;
    local least_collateral_ratio_position: PositionDetailsForRiskManagement;
    local least_collateral_ratio_position_collateral_price;
    local least_collateral_ratio_position_asset_price;
    if (is_lesser == TRUE) {
        assert least_collateral_ratio = collateral_ratio_position;
        assert least_collateral_ratio_position = [positions_];
        assert least_collateral_ratio_position_asset_price = market_price.price;
    } else {
        assert least_collateral_ratio = least_collateral_ratio_;
        assert least_collateral_ratio_position = least_collateral_ratio_position_;
        assert least_collateral_ratio_position_asset_price = least_collateral_ratio_position_asset_price_;
    }

    // Recurse over to the next position
    return check_liquidation_recurse(
        account_address_=account_address_,
        market_address_=market_address_,
        market_price_address_=market_price_address_,
        positions_len_=positions_len_ - 1,
        positions_=positions_ + PositionDetailsForRiskManagement.SIZE,
        collateral_id_=collateral_id_,
        total_account_value_=total_account_value_ + position_value,
        total_maintenance_requirement_=total_maintenance_requirement_ + maintenance_requirement,
        least_collateral_ratio_=least_collateral_ratio,
        least_collateral_ratio_position_=least_collateral_ratio_position,
        least_collateral_ratio_position_asset_price_=least_collateral_ratio_position_asset_price,
    );
}

// @notice Function to calculate amount to be put on sale for deleveraging
// @param account_address_ - account address of the user
// @param position - position to be deleveraged
// @param market_address - Address of the Market contract
// @param position - direction of the position to be deleveraged
// @param asset_price_ - asset price of the asset in the position
// @return amount_to_sold - amount to be put on sale for deleveraging
func check_deleveraging{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_address_: felt,
    market_address_: felt,
    position_: PositionDetailsForRiskManagement,
    asset_price_: felt,
) -> (amount_to_be_sold: felt) {
    alloc_locals;

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

    // Calculate amount to be sold for deleveraging
    let (maintenance_requirement) = Math64x61_mul(req_margin, asset_price_);
    let (price_diff_maintenance) = Math64x61_sub(maintenance_requirement, price_diff);
    let (amount_to_be_present) = Math64x61_div(margin_amount, price_diff_maintenance);
    let (amount_to_be_sold) = Math64x61_sub(position_size, amount_to_be_present);

    // Calculate the leverage after deleveraging
    let (position_value) = Math64x61_add(margin_amount, borrowed_amount);
    let (amount_to_be_sold_value) = Math64x61_mul(amount_to_be_sold, asset_price_);
    let (remaining_position_value) = Math64x61_sub(position_value, amount_to_be_sold_value);
    let (leverage_after_deleveraging) = Math64x61_div(remaining_position_value, margin_amount);

    // to64x61(2) == 4611686018427387904
    let can_be_liquidated = is_le(leverage_after_deleveraging, 4611686018427387904);
    if (can_be_liquidated == TRUE) {
        return (0,);
    } else {
        // position_to_be_deleveraged event is emitted
        position_to_be_deleveraged.emit(position=position_, amount_to_be_sold=amount_to_be_sold);
        return (amount_to_be_sold,);
    }
}
