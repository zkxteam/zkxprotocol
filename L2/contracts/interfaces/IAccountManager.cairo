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

    func get_public_key() -> (res: felt) {
    }

    func return_array_collaterals() -> (array_list_len: felt, array_list: CollateralBalance*) {
    }

    func get_deleveragable_or_liquidatable_position(collateral_id_: felt) -> (
        position: LiquidatablePosition
    ) {
    }

    // External functions

    func execute_order(
        request: OrderRequest,
        signature: Signature,
        size: felt,
        execution_price: felt,
        margin_amount: felt,
        borrowed_amount: felt,
        market_id: felt,
        collateral_id_: felt,
        fee: felt,
        pnl: felt,
        side: felt,
    ) -> (res: felt) {
    }

    func update_withdrawal_history(request_id_: felt) {
    }

    func transfer_from(assetID_: felt, amount_: felt, invoked_for_: felt) -> () {
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

    func transfer(assetID_: felt, amount_: felt, invoked_for_: felt) -> () {
    }

    func liquidate_position(
        collateral_id_: felt, position_: PositionDetailsForRiskManagement, amount_to_be_sold_: felt
    ) {
    }
}
