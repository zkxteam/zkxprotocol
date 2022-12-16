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
    PositionDetailsWithMarket,
)
from contracts.interfaces.IAccountManager import IAccountManager
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.ICollateralPrices import ICollateralPrices
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

@storage_var
func debug(id: felt) -> (res: felt) {
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

@view
func return_position_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    index: felt
) -> (res: felt) {
    let (_acc_value) = debug.read(id=index);
    return (res=_acc_value);
}

// //////////
// Events //
// //////////

// Event emitted whenever check_liquidation() is called
@event
func check_liquidation_called(
    account_address: felt,
    liq_result: felt,
    least_collateral_ratio_position: PositionDetailsWithMarket,
) {
}

// Event emitted whenever check_order_can_be_opened() is called
@event
func can_order_be_opened(order: MultipleOrder) {
}

// Event emitted whenever position can be deleveraged
@event
func position_to_be_deleveraged(position: PositionDetailsWithMarket, amount_to_be_sold: felt) {
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
func check_liquidation{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_address: felt, prices_len: felt, prices: PriceData*
) -> (liq_result: felt, least_collateral_ratio_position: PositionDetailsWithMarket) {
    alloc_locals;
    // Check if the caller is a node

    // Check if the list is empty
    with_attr error_message("Liquidate: Prices array cannot be empty") {
        assert_not_zero(prices_len);
    }

    // Fetch all the positions from the Account contract
    let (
        positions_len: felt, positions: PositionDetailsWithMarket*
    ) = IAccountManager.get_positions(contract_address=account_address);

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

    // Recurse through all positions to see if it needs to liquidated
    let (
        liq_result,
        least_collateral_ratio_position,
        least_collateral_ratio_position_collateral_price,
        least_collateral_ratio_position_asset_price,
    ) = check_liquidation_recurse(
        account_address=account_address,
        market_address=market_address,
        positions_len=positions_len,
        positions=positions,
        prices_len=prices_len,
        prices=prices,
        total_account_value=0,
        total_maintenance_requirement=0,
        least_collateral_ratio=Math64x61_ONE,
        least_collateral_ratio_position=PositionDetailsWithMarket(0, 0, 0, 0, 0, 0, 0),
        least_collateral_ratio_position_collateral_price=0,
        least_collateral_ratio_position_asset_price=0,
    );

    if (liq_result == TRUE) {
        let (amount_to_be_sold) = check_deleveraging(
            account_address,
            market_address,
            least_collateral_ratio_position,
            least_collateral_ratio_position_collateral_price,
            least_collateral_ratio_position_asset_price,
        );
        IAccountManager.liquidate_position(
            contract_address=account_address,
            position_=least_collateral_ratio_position,
            amount_to_be_sold_=amount_to_be_sold,
        );
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    // check_liquidation_called event is emitted
    check_liquidation_called.emit(
        account_address=account_address,
        liq_result=liq_result,
        least_collateral_ratio_position=least_collateral_ratio_position,
    );

    return (liq_result, least_collateral_ratio_position);
}

// @notice Function to check if order can be opened
// @param order - MultipleOrder structure
// @param size - matched order size of current order
// @param execution_price - Execution price of current order
@external
func check_order_can_be_opened{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order: MultipleOrder, size: felt, execution_price: felt
) {
    can_order_be_opened.emit(order=order);

    let (prices_len: felt, prices: PriceData*) = get_asset_prices(order.user_address);
    if (prices_len != 0) {
        check_for_risk(order, size, execution_price, prices_len, prices);
        return ();
    }

    return ();
}

// ////////////
// Internal //
// ////////////

// @notice Finds the usd value of all the collaterals in account contract
// @param prices_len - Length of the prices array
// @param prices - Array containing prices of corresponding collaterals in collaterals array
// @param collaterals_len - Length of the collateral array
// @param collaterals - Array containing balance of each collateral of the user
// @param total_value - Stores the total value in usd of all the collaterals recursed over
// @return usd_value - Value of the collaterals held by user in usd
func find_collateral_balance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    prices_len: felt,
    prices: PriceData*,
    collaterals_len: felt,
    collaterals: CollateralBalance*,
    total_value: felt,
) -> (usd_value: felt) {
    // If the length of the collateral array is 0, return
    if (collaterals_len == 0) {
        return (total_value,);
    }

    // Create a temporary struct to read data from the array element of prices
    tempvar price_details: PriceData = PriceData(
        assetID=[prices].assetID,
        collateralID=[prices].collateralID,
        assetPrice=[prices].assetPrice,
        collateralPrice=[prices].collateralPrice
        );

    // Create a temporary struct to read data from the array element of collaterals
    tempvar collateral_details: CollateralBalance = CollateralBalance(
        assetID=[collaterals].assetID,
        balance=[collaterals].balance
        );
    // Check if the passed prices list is in proper order and the price is not negative
    with_attr error_message("Liquidate: AssetID and collateralID mismatch") {
        assert price_details.collateralID = collateral_details.assetID;
        assert_nn(price_details.collateralPrice);
        assert price_details.assetPrice = 0;
    }

    // Calculate the value of the current collateral
    let (collateral_value_usd) = Math64x61_mul(
        collateral_details.balance, price_details.collateralPrice
    );

    let (new_total_account_value) = Math64x61_add(total_value, collateral_value_usd);

    // Recurse over the next element
    return find_collateral_balance(
        prices_len=prices_len - 1,
        prices=prices + PriceData.SIZE,
        collaterals_len=collaterals_len - 1,
        collaterals=collaterals + CollateralBalance.SIZE,
        total_value=new_total_account_value,
    );
}

// @notice Function that is called recursively by check_recurse
// @param account_address - Account address of the user
// @param market_address - Markets contarct address
// @param positions_len - Length of the positions array
// @param postions - Array with all the position details
// @param prices_len - Length of the prices array
// @param prices - Array with all the price details
// @param total_account_value - Collateral value - borrowed value + positionSize * price
// @param total_maintenance_requirement - maintenance ratio of the asset * value of the position when executed
// @param least_collateral_ratio - The least collateral ratio among the positions
// @param least_collateral_ratio_position - The position which is having the least collateral ratio
// @param least_collateral_ratio_position_collateral_price - Collateral price of the collateral in the postion which is having the least collateral ratio
// @param least_collateral_ratio_position_asset_price - Asset price of an asset in the postion which is having the least collateral ratio
// @return is_liquidation - 1 if positions are marked to be liquidated
// @return least_collateral_ratio_position - The least collateralized position
// @return least_collateral_ratio_position_collateral_price - Collateral price of the collateral in least_collateral_ratio_position
// @return least_collateral_ratio_position_asset_price - Asset price of an asset in least_collateral_ratio_position
func check_liquidation_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_address: felt,
    market_address: felt,
    positions_len: felt,
    positions: PositionDetailsWithMarket*,
    prices_len: felt,
    prices: PriceData*,
    total_account_value: felt,
    total_maintenance_requirement: felt,
    least_collateral_ratio: felt,
    least_collateral_ratio_position: PositionDetailsWithMarket,
    least_collateral_ratio_position_collateral_price: felt,
    least_collateral_ratio_position_asset_price: felt,
) -> (
    is_liquidation: felt,
    least_collateral_ratio_position: PositionDetailsWithMarket,
    least_collateral_ratio_position_collateral_price: felt,
    least_collateral_ratio_position_asset_price: felt,
) {
    alloc_locals;

    // Check if the list is empty, if yes return the result
    if (positions_len == 0) {
        // Fetch all the collaterals that the user holds
        let (
            collaterals_len: felt, collaterals: CollateralBalance*
        ) = IAccountManager.return_array_collaterals(contract_address=account_address);

        // Calculate the value of all the collaterals in usd
        let (user_balance) = find_collateral_balance(
            prices_len=prices_len,
            prices=prices,
            collaterals_len=collaterals_len,
            collaterals=collaterals,
            total_value=0,
        );

        // Add the collateral value to the total_account_value
        local total_account_value_collateral = total_account_value + user_balance;

        // /////////////////
        // TO BE REMOVED //
        maintenance.write(total_maintenance_requirement);
        acc_value.write(total_account_value);
        // /////////////////

        // Check if the maintenance margin is not satisfied
        let is_liquidation = is_le(total_account_value_collateral, total_maintenance_requirement);

        // Return if the account should be liquidated or not and the orderId of the least colalteralized position
        return (
            is_liquidation,
            least_collateral_ratio_position,
            least_collateral_ratio_position_collateral_price,
            least_collateral_ratio_position_asset_price,
        );
    }

    // Create a temporary struct to read data from the array element of positions
    tempvar position_details: PositionDetailsWithMarket = PositionDetailsWithMarket(
        market_id=[positions].market_id,
        direction=[positions].direction,
        avg_execution_price=[positions].avg_execution_price,
        position_size=[positions].position_size,
        margin_amount=[positions].margin_amount,
        borrowed_amount=[positions].borrowed_amount,
        leverage=[positions].leverage
        );

    // Get the asset ID and collateral ID of the position
    let (asset_id: felt, collateral_id: felt) = IMarkets.get_asset_collateral_from_market(
        contract_address=market_address, market_id_=position_details.market_id
    );

    // Create a temporary struct to read data from the array element of prices
    tempvar price_details: PriceData = PriceData(
        assetID=[prices].assetID,
        collateralID=[prices].collateralID,
        assetPrice=[prices].assetPrice,
        collateralPrice=[prices].collateralPrice
        );

    // Check if there is a mismatch in prices array and positions array
    with_attr error_message("Liquidate: AssetID and collateralID mismatch") {
        assert asset_id = price_details.assetID;
        assert collateral_id = price_details.collateralID;
    }

    // Check if the prices are not negative
    with_attr error("Liquidate: Invalid prices for collateral/asset") {
        assert_nn(price_details.collateralPrice);
        assert_nn(price_details.assetPrice);
    }

    // Get the maintanence margin from Markets contract
    let (market_id) = IMarkets.get_market_id_from_assets(
        contract_address=market_address,
        asset_id_=price_details.assetID,
        collateral_id_=price_details.collateralID,
    );
    let (req_margin) = IMarkets.get_maintenance_margin(
        contract_address=market_address, market_id_=market_id
    );

    // Calculate the required margin in usd
    let (maintenance_position) = Math64x61_mul(
        position_details.avg_execution_price, position_details.position_size
    );
    let (maintenance_requirement) = Math64x61_mul(req_margin, maintenance_position);
    let (maintenance_requirement_usd) = Math64x61_mul(
        maintenance_requirement, price_details.collateralPrice
    );

    // Calculate pnl to check if it is the least collateralized position
    local test_;
    local price_diff_;
    if (position_details.direction == 1) {
        tempvar price_diff = price_details.assetPrice - position_details.avg_execution_price;
        price_diff_ = price_diff;
        test_ = 0;
    } else {
        tempvar price_diff = position_details.avg_execution_price - price_details.assetPrice;
        price_diff_ = price_diff;
        test_ = price_diff;
    }

    let (pnl) = Math64x61_mul(price_diff_, position_details.position_size);

    debug.write(id=positions_len, value=test_);
    // Calculate the value of the current account margin in usd
    local position_value = maintenance_position - position_details.borrowed_amount + pnl;

    let (net_position_value_usd: felt) = Math64x61_mul(
        position_value, price_details.collateralPrice
    );

    // Margin ratio calculation
    local numerator = position_details.margin_amount + pnl;
    let (denominator) = Math64x61_mul(position_details.position_size, price_details.assetPrice);
    let (collateral_ratio_position) = Math64x61_div(numerator, denominator);

    let is_lesser = is_le(collateral_ratio_position, least_collateral_ratio);

    // If it is the lowest, update least_collateral_ratio and least_collateral_ratio_position
    local least_collateral_ratio_;
    local least_collateral_ratio_position_: PositionDetailsWithMarket;
    local least_collateral_ratio_position_collateral_price_;
    local least_collateral_ratio_position_asset_price_;
    if (is_lesser == TRUE) {
        assert least_collateral_ratio_ = collateral_ratio_position;
        assert least_collateral_ratio_position_ = position_details;
        assert least_collateral_ratio_position_collateral_price_ = price_details.collateralPrice;
        assert least_collateral_ratio_position_asset_price_ = price_details.assetPrice;
    } else {
        assert least_collateral_ratio_ = least_collateral_ratio;
        assert least_collateral_ratio_position_ = least_collateral_ratio_position;
        assert least_collateral_ratio_position_collateral_price_ = least_collateral_ratio_position_collateral_price;
        assert least_collateral_ratio_position_asset_price_ = least_collateral_ratio_position_asset_price;
    }

    // Recurse over to the next position
    return check_liquidation_recurse(
        account_address=account_address,
        market_address=market_address,
        positions_len=positions_len - 1,
        positions=positions + PositionDetailsWithMarket.SIZE,
        prices_len=prices_len - 1,
        prices=prices + PriceData.SIZE,
        total_account_value=total_account_value + net_position_value_usd,
        total_maintenance_requirement=total_maintenance_requirement + maintenance_requirement_usd,
        least_collateral_ratio=least_collateral_ratio_,
        least_collateral_ratio_position=least_collateral_ratio_position_,
        least_collateral_ratio_position_collateral_price=least_collateral_ratio_position_collateral_price_,
        least_collateral_ratio_position_asset_price=least_collateral_ratio_position_asset_price_,
    );
}

// @notice Function to calculate amount to be put on sale for deleveraging
// @param account_address_ - account address of the user
// @param position - position to be deleveraged
// @param market_address - Address of the Market contract
// @param position - direction of the position to be deleveraged
// @param collateral_price_ - collateral price of the collateral in the position
// @param asset_price_ - asset price of the asset in the position
// @return amount_to_sold - amount to be put on sale for deleveraging
func check_deleveraging{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_address_: felt,
    market_address_: felt,
    position_: PositionDetailsWithMarket,
    collateral_price_: felt,
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

    // Calcculate amount to be sold for deleveraging
    let (margin_amount_in_usd) = Math64x61_mul(margin_amount, collateral_price_);
    let (maintenance_requirement_in_usd) = Math64x61_mul(req_margin, asset_price_);
    let (price_diff_in_usd) = Math64x61_sub(maintenance_requirement_in_usd, price_diff);
    let (amount_to_be_present) = Math64x61_div(margin_amount_in_usd, price_diff_in_usd);
    let (amount_to_be_sold) = Math64x61_sub(position_size, amount_to_be_present);

    // Calculate the leverage after deleveraging
    let (position_value) = Math64x61_add(margin_amount, borrowed_amount);
    let (position_value_in_usd) = Math64x61_mul(position_value, collateral_price_);
    let (amount_to_be_sold_value_in_usd) = Math64x61_mul(amount_to_be_sold, asset_price_);
    let (remaining_position_value_in_usd) = Math64x61_sub(
        position_value_in_usd, amount_to_be_sold_value_in_usd
    );
    let (leverage_after_deleveraging) = Math64x61_div(
        remaining_position_value_in_usd, margin_amount_in_usd
    );

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

// @notice Internal function to check if position can be opened
// @param order - MultipleOrder structure
// @param size - matched order size of current order
// @param execution_price - Execution price of current order
// @param prices_len - Length of the prices array
// @param prices - Array with all the price details
func check_for_risk{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order: MultipleOrder, size: felt, execution_price: felt, prices_len: felt, prices: PriceData*
) {
    alloc_locals;

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get a list with all positions from AccountManager contract
    let (
        positions_len: felt, positions: PositionDetailsWithMarket*
    ) = IAccountManager.get_positions(contract_address=order.user_address);

    // Fetch the maintanence margin requirement from Markets contract
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    let (req_margin) = IMarkets.get_maintenance_margin(
        contract_address=market_address, market_id_=order.market_id
    );

    let (asset_id, collateral_id) = IMarkets.get_asset_collateral_from_market(
        contract_address=market_address, market_id_=order.market_id
    );

    // Get collateral price
    let (collateral_price_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=CollateralPrices_INDEX, version=version
    );
    let (collateral_price: CollateralPrice) = ICollateralPrices.get_collateral_price(
        contract_address=collateral_price_address, id=collateral_id
    );

    // Calculate needed values
    let (leveraged_position_value) = Math64x61_mul(execution_price, size);

    let (leveraged_position_value_collateral) = Math64x61_mul(
        leveraged_position_value, collateral_price.price_in_usd
    );
    let (total_position_value) = Math64x61_div(leveraged_position_value_collateral, order.leverage);
    let (amount_to_be_borrowed) = Math64x61_sub(
        leveraged_position_value_collateral, total_position_value
    );

    let (account_value) = Math64x61_sub(leveraged_position_value_collateral, amount_to_be_borrowed);
    let (maintenance_requirement) = Math64x61_mul(req_margin, leveraged_position_value_collateral);

    // Recurse through all positions to see if it needs to liquidated
    let (
        liq_result,
        least_collateral_ratio_position,
        least_collateral_ratio_position_collateral_price,
        least_collateral_ratio_position_asset_price,
    ) = check_liquidation_recurse(
        account_address=order.user_address,
        market_address=market_address,
        positions_len=positions_len,
        positions=positions,
        prices_len=prices_len,
        prices=prices,
        total_account_value=account_value,
        total_maintenance_requirement=maintenance_requirement,
        least_collateral_ratio=Math64x61_ONE,
        least_collateral_ratio_position=PositionDetailsWithMarket(0, 0, 0, 0, 0, 0, 0),
        least_collateral_ratio_position_collateral_price=0,
        least_collateral_ratio_position_asset_price=0,
    );

    with_attr error_message("Liquidate: Position doesn't satisfy maintanence margin") {
        assert liq_result = FALSE;
    }
    return ();
}

// @notice Internal function to populate prices
// @param market_contract_address - Address of Market contract
// @param market_price_address - Address of Market Price contract
// @param collateral_price_address - Address of Collateral Price contract
// @param iterator - Index of the position_array currently pointing to
// @param positions_len - Length of the positions array
// @param postions - Array with all the position details
// @param prices_len - Length of the prices array
// @param prices - Array with all the price details
// @return prices_len - Length of prices array
// @return prices - Fully populated prices
func populate_asset_prices_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_contract_address: felt,
    market_price_address: felt,
    collateral_price_address: felt,
    iterator: felt,
    positions_len: felt,
    positions: PositionDetailsWithMarket*,
    prices_len: felt,
    prices: PriceData*,
) -> (prices_len: felt, prices: PriceData*) {
    alloc_locals;

    if (iterator == positions_len) {
        return (prices_len, prices);
    }

    // Get the asset & collateral ID from market contract
    let (asset_id: felt, collateral_id: felt) = IMarkets.get_asset_collateral_from_market(
        contract_address=market_contract_address, market_id_=[positions].market_id
    );
    let (market_price: MarketPrice) = IMarketPrices.get_market_price(
        contract_address=market_price_address, id=[positions].market_id
    );

    // Get the market ttl from the market contract
    let (market_ttl: felt) = IMarkets.get_ttl_from_market(
        contract_address=market_contract_address, market_id_=[positions].market_id
    );

    // Get the collateral price from the CollateralPrice contract
    let (collateral_price: CollateralPrice) = ICollateralPrices.get_collateral_price(
        contract_address=collateral_price_address, id=collateral_id
    );

    // Calculate the timestamp
    let (current_timestamp) = get_block_timestamp();
    tempvar ttl = market_ttl;
    tempvar timestamp = market_price.timestamp;
    tempvar time_difference = current_timestamp - timestamp;

    let status = is_le(time_difference, ttl);
    if (status == TRUE) {
        let (asset_price_in_usd) = Math64x61_mul(market_price.price, collateral_price.price_in_usd);
        let price_data = PriceData(
            assetID=asset_id,
            collateralID=collateral_id,
            assetPrice=asset_price_in_usd,
            collateralPrice=collateral_price.price_in_usd,
        );
        assert prices[prices_len] = price_data;

        return populate_asset_prices_recurse(
            market_contract_address,
            market_price_address,
            collateral_price_address,
            iterator + 1,
            positions_len,
            positions + PositionDetailsWithMarket.SIZE,
            prices_len + 1,
            prices,
        );
    }
    let (empty_price_array: PriceData*) = alloc();
    return (0, empty_price_array);
}

// @notice Internal function to populate collateral prices
// @param collateral_price_address - Address of Collateral Price contract
// @param iterator - Index of the position_array currently pointing to
// @param collaterals_len - Length of the collaterals array
// @param collaterals - Array with all the collateral details
// @param prices_len - Length of the prices array
// @param prices - Array with all the price details
// @return prices_len - Length of prices array
// @return prices - Fully populated prices
func populate_collateral_prices_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    collateral_price_address: felt,
    iterator: felt,
    collaterals_len: felt,
    collaterals: CollateralBalance*,
    prices_len: felt,
    prices: PriceData*,
) -> (prices_len: felt, prices: PriceData*) {
    alloc_locals;
    if (iterator == collaterals_len) {
        return (prices_len, prices);
    }

    let (collateral_price: CollateralPrice) = ICollateralPrices.get_collateral_price(
        contract_address=collateral_price_address, id=[collaterals].assetID
    );

    let price_data = PriceData(
        assetID=0,
        collateralID=[collaterals].assetID,
        assetPrice=0,
        collateralPrice=collateral_price.price_in_usd,
    );

    assert prices[prices_len] = price_data;
    return populate_collateral_prices_recurse(
        collateral_price_address,
        iterator + 1,
        collaterals_len,
        collaterals + CollateralBalance.SIZE,
        prices_len + 1,
        prices,
    );
}

// @notice Internal function to get asset prices
// @param account_address - Address of L2 account contract
// @return prices_len - Length of prices array
// @return prices - Fully populated prices
func get_asset_prices{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_address: felt
) -> (prices_len: felt, prices: PriceData*) {
    alloc_locals;

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (prices: PriceData*) = alloc();

    // Get market price contract address
    let (market_prices_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=MarketPrices_INDEX, version=version
    );

    // Get market contract address
    let (market_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get collateral price contract address
    let (collateral_prices_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=CollateralPrices_INDEX, version=version
    );

    // Fetch all the positions from the Account contract
    let (
        positions_len: felt, positions: PositionDetailsWithMarket*
    ) = IAccountManager.get_positions(contract_address=account_address);

    let (prices_array_len: felt, prices_array: PriceData*) = populate_asset_prices_recurse(
        market_contract_address=market_contract_address,
        market_price_address=market_prices_address,
        collateral_price_address=collateral_prices_address,
        iterator=0,
        positions_len=positions_len,
        positions=positions,
        prices_len=0,
        prices=prices,
    );
    if (prices_array_len == 0) {
        let (empty_price_array: PriceData*) = alloc();
        return (0, empty_price_array);
    }

    // Fetch all the collaterals that the user holds
    let (
        collaterals_len: felt, collaterals: CollateralBalance*
    ) = IAccountManager.return_array_collaterals(contract_address=account_address);

    if (collaterals_len == 0) {
        let (empty_collateral_array: PriceData*) = alloc();
        return (0, empty_collateral_array);
    }

    return populate_collateral_prices_recurse(
        collateral_price_address=collateral_prices_address,
        iterator=0,
        collaterals_len=collaterals_len,
        collaterals=collaterals,
        prices_len=prices_array_len,
        prices=prices_array,
    );
}
