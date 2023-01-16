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
    func execute_order(
        request: OrderRequest,
        signature: Signature,
        size: felt,
        execution_price: felt,
        margin_amount: felt,
        borrowed_amount: felt,
        market_id: felt,
        pnl: felt,
    ) -> (res: felt) {
    }

    func update_withdrawal_history(request_id_: felt) {
    }

    func transfer_from(assetID_: felt, amount: felt) -> () {
    }

    func get_position_data(market_id_: felt, direction_: felt) -> (res: PositionDetails) {
    }

    func transfer(assetID_: felt, amount: felt) -> () {
    }

    func get_balance(assetID_: felt) -> (res: felt) {
    }

    func get_positions() -> (positions_array_len: felt, positions_array: PositionDetailsWithMarket*) {
    }

    func get_positions_for_risk_management() -> (positions_array_len: felt, positions_array: PositionDetailsForRiskManagement*) {
    }

    func get_simplified_positions(timestamp_filter_: felt) -> (
        positions_array_len: felt, positions_array: SimplifiedPosition*
    ) {
    }

    func get_portion_executed(order_id_: felt) -> (res: felt) {
    }

    func transfer_from_abr(
        collateral_id_: felt, market_id_: felt, direction_: felt, amount_: felt
    ) {
    }

    func transfer_abr(collateral_id_: felt, market_id_: felt, direction_: felt, amount_: felt) {
    }

    func timestamp_check(market_id_: felt) -> (is_eight_hours: felt) {
    }

    func get_public_key() -> (res: felt) {
    }

    func return_array_collaterals() -> (array_list_len: felt, array_list: CollateralBalance*) {
    }

    func liquidate_position(position_: PositionDetailsForRiskManagement, amount_to_be_sold_: felt) {
    }

    func get_deleveragable_or_liquidatable_position() -> (position: LiquidatablePosition) {
    }
}
