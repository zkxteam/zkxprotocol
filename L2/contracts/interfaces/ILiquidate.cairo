%lang starknet

from contracts.DataTypes import PriceData, MultipleOrder, PositionDetailsForRiskManagement

@contract_interface
namespace ILiquidate {
    // View functions

    func return_acc_value() -> (res: felt) {
    }

    func return_maintenance() -> (res: felt) {
    }

    // External functions

    func check_for_risk(order_: MultipleOrder, size: felt, execution_price_: felt, margin_amount_:felt) -> (available_margin: felt){
    }

    func mark_under_collateralized_position(account_address_: felt, collateral_id_: felt) -> (
        liq_result: felt,
        least_collateral_ratio_position: PositionDetailsForRiskManagement,
        total_account_value: felt,
        total_maintenance_requirement: felt,
    ){
    }
}
