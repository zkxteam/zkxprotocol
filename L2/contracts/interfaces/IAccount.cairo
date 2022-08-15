%lang starknet

from contracts.DataTypes import OrderRequest, OrderDetails, Signature, OrderDetailsWithIDs, CollateralBalance

@contract_interface
namespace IAccount:
    func execute_order(
        request : OrderRequest,
        signature : Signature,
        size : felt,
        execution_price : felt,
        margin_amount : felt,
        borrowed_amount : felt,
    ) -> (res : felt):
    end

    func update_withdrawal_history(
        request_id_ : felt,
    ):
    end

    func transfer_from(assetID_ : felt, amount : felt) -> ():
    end

    func get_order_data(order_ID : felt) -> (res : OrderDetails):
    end

    func transfer(assetID_ : felt, amount : felt) -> ():
    end

    func get_balance(assetID_ : felt) -> (res : felt):
    end

    func return_array_positions() -> (array_list_len : felt, array_list : OrderDetailsWithIDs*):
    end

    func transfer_from_abr(orderID_ : felt, assetID_ : felt, marketID_ : felt, amount : felt):
    end

    func transfer_abr(orderID_ : felt, assetID_ : felt, marketID_ : felt, amount : felt):
    end

    func timestamp_check(orderID_ : felt) -> (is_eight_hours : felt):
    end

    func get_public_key() -> (res : felt):
    end

    func return_array_collaterals() -> (array_list_len : felt, array_list : CollateralBalance*):
    end

    func liquidate_position(id : felt, amount : felt) -> ():
    end
end
