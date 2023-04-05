%lang starknet

from contracts.DataTypes import (
    CollateralBalance,
    LiquidatablePosition,
    OrderRequest,
    PositionDetails,
    PositionDetailsForRiskManagement,
    PositionDetailsWithMarket,
    Signature,
    SimplifiedPosition,
)

@contract_interface
namespace IAccountManager {
    // View functions

    func get_position_data(market_id_: felt, direction_: felt) -> (res: PositionDetails) {
    }

    func get_balance(assetID_: felt) -> (res: felt) {
    }

    func get_unused_balance(assetID_: felt) -> (res: felt) {
    }

    func get_positions() -> (
        positions_array_len: felt, positions_array: PositionDetailsWithMarket*
    ) {
    }

    func get_positions_for_risk_management(collateral_id_: felt) -> (
        positions_array_len: felt, positions_array: PositionDetailsForRiskManagement*
    ) {
    }

    func get_simplified_positions(timestamp_filter_: felt) -> (
        positions_array_len: felt, positions_array: SimplifiedPosition*
    ) {
    }

    func get_portion_executed(order_id_: felt) -> (res: felt) {
    }

    func get_public_key() -> (pub_key: felt, auth_reg_addr: felt) {
    }

    func return_array_collaterals() -> (array_list_len: felt, array_list: CollateralBalance*) {
    }

    func get_deleveragable_or_liquidatable_position(collateral_id_: felt) -> (
        position: LiquidatablePosition
    ) {
    }

    func get_margin_info(
        asset_id_: felt, new_position_maintanence_requirement_: felt, new_position_margin_: felt
    ) -> (
        is_liquidation: felt,
        total_margin: felt,
        available_margin: felt,
        unrealized_pnl_sum: felt,
        maintenance_margin_requirement: felt,
        least_collateral_ratio: felt,
        least_collateral_ratio_position: PositionDetailsForRiskManagement,
        least_collateral_ratio_position_asset_price: felt,
    ) {
    }

    // External functions

    func execute_order(
        request: OrderRequest,
        signature: Signature,
        size: felt,
        average_execution_price: felt,
        execution_price: felt,
        margin_amount: felt,
        borrowed_amount: felt,
        market_id: felt,
        collateral_id_: felt,
        pnl: felt,
        opening_fee: felt,
        side: felt,
        margin_lock_update_amount: felt,
    ) -> (res: felt) {
    }

    func update_withdrawal_history(request_id_: felt) {
    }

    func transfer_from(asset_id_: felt, market_id_: felt, amount_: felt, invoked_for_: felt) -> () {
    }

    func transfer_from_abr(
        collateral_id_: felt,
        market_id_: felt,
        direction_: felt,
        amount_: felt,
        abr_value_: felt,
        position_size_: felt,
    ) {
    }

    func transfer_abr(
        collateral_id_: felt,
        market_id_: felt,
        direction_: felt,
        amount_: felt,
        abr_value_: felt,
        position_size_: felt,
    ) {
    }

    func transfer(asset_id_: felt, market_id_: felt, amount_: felt, invoked_for_: felt) -> () {
    }

    func liquidate_position(
        collateral_id_: felt, position_: PositionDetailsForRiskManagement, amount_to_be_sold_: felt
    ) {
    }
}
