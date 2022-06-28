%lang starknet

from contracts.DataTypes import OrderRequest, OrderDetails, Signature, OrderDetailsWithIDs

@contract_interface
namespace IAccountTimestamp:
    func execute_order(
        request : OrderRequest,
        signature : Signature,
        size : felt,
        execution_price : felt,
        margin_amount : felt,
        borrowed_amount : felt,
    ) -> (res : felt):
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

    func transfer_from_abr(assetID_ : felt, marketID_ : felt, amount : felt):
    end

    func transfer_abr(assetID_ : felt, marketID_ : felt, amount : felt):
    end

    func timestamp_check(market_id : felt) -> (is_eight_hours : felt):
    end
end
