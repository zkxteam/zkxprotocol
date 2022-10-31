%lang starknet

from contracts.DataTypes import (
    CollateralBalance,
    LiquidatablePosition,
    NetPositions,
    OrderRequest,
    PositionDetails,
    PositionDetailsWithMarket,
    Signature,
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

    func get_positions() -> (array_list_len: felt, array_list: PositionDetailsWithMarket*) {
    }

    func get_net_positions() -> (
        net_positions_array_len: felt, net_positions_array: NetPositions*
    ) {
    }

    func transfer_from_abr(collateral_id_: felt, market_id_: felt, amount_: felt) {
    }

    func transfer_abr(collateral_id_: felt, market_id_: felt, amount_: felt) {
    }

    func timestamp_check(market_id_: felt) -> (is_eight_hours: felt) {
    }

    func get_public_key() -> (res: felt) {
    }

    func return_array_collaterals() -> (array_list_len: felt, array_list: CollateralBalance*) {
    }

    func liquidate_position(position_: PositionDetailsWithMarket, amount_to_be_sold_: felt) {
    }

    func get_deleveragable_or_liquidatable_position() -> (position: LiquidatablePosition) {
    }

    func get_portion_executed(order_id: felt) -> (portion_executed: felt) {
    }
}
