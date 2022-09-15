%lang starknet

from contracts.DataTypes import (
    CollateralBalance,
    NetPositions,
    OrderRequest,
    PositionDetails,
    PositionDetailsWithIDs,
    Signature,
)

@contract_interface
namespace IAccountManager:
    func execute_order(
        request : OrderRequest,
        signature : Signature,
        size : felt,
        execution_price : felt,
        margin_amount : felt,
        borrowed_amount : felt,
        market_id : felt,
    ) -> (res : felt):
    end

    func update_withdrawal_history(request_id_ : felt):
    end

    func transfer_from(assetID_ : felt, amount : felt) -> ():
    end

    func get_position_data(market_id_ : felt, direction_ : felt) -> (res : PositionDetails):
    end

    func transfer(assetID_ : felt, amount : felt) -> ():
    end

    func get_balance(assetID_ : felt) -> (res : felt):
    end

    func get_positions() -> (array_list_len : felt, array_list : PositionDetailsWithIDs*):
    end

    func get_net_positions() -> (
        net_positions_array_len : felt, net_positions_array : NetPositions*
    ):
    end

    func transfer_from_abr(collateral_id_ : felt, market_id_ : felt, amount_ : felt):
    end

    func transfer_abr(collateral_id_ : felt, market_id_ : felt, amount_ : felt):
    end

    func timestamp_check(market_id_ : felt) -> (is_eight_hours : felt):
    end

    func get_public_key() -> (res : felt):
    end

    func return_array_collaterals() -> (array_list_len : felt, array_list : CollateralBalance*):
    end

    func liquidate_position(id : felt, amount : felt) -> ():
    end
end
