%lang starknet

from contracts.DataTypes import OrderRequest, OrderDetails, Signature

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
        collateral_id_ : felt,
        amount_ : felt,
        timestamp_ : felt,
        node_operator_L1_address_ : felt,
        L1_fee_amount_ : felt,
        L1_fee_collateral_id_ : felt,
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

    func get_public_key() -> (res : felt):
    end
end
