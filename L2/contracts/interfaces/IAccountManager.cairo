%lang starknet

from contracts.DataTypes import (
    OrderRequest,
    OrderDetails,
    Signature,
    OrderDetailsWithIDs,
    CollateralBalance,
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
    ) -> (res: felt) {
    }

    func update_withdrawal_history(request_id_: felt) {
    }

    func transfer_from(assetID_: felt, amount: felt) -> () {
    }

    func get_order_data(order_ID: felt) -> (res: OrderDetails) {
    }

    func transfer(assetID_: felt, amount: felt) -> () {
    }

    func get_balance(assetID_: felt) -> (res: felt) {
    }

    func return_array_positions() -> (array_list_len: felt, array_list: OrderDetailsWithIDs*) {
    }

    func transfer_from_abr(orderID_: felt, assetID_: felt, marketID_: felt, amount: felt) {
    }

    func transfer_abr(orderID_: felt, assetID_: felt, marketID_: felt, amount: felt) {
    }

    func timestamp_check(orderID_: felt) -> (is_eight_hours: felt) {
    }

    func get_public_key() -> (res: felt) {
    }

    func return_array_collaterals() -> (array_list_len: felt, array_list: CollateralBalance*) {
    }

    func liquidate_position(id: felt, amount: felt) -> () {
    }
}
