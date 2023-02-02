%lang starknet

from contracts.DataTypes import PriceData, MultipleOrder, PositionDetailsForRiskManagement

@contract_interface
namespace ILiquidate {
    func find_under_collateralized_position(account_address_: felt, collateral_id_: felt) -> (
        liq_result: felt,
        least_collateral_ratio_position: PositionDetailsForRiskManagement,
        total_account_value: felt,
        total_maintenance_requirement: felt,
    ) {
    }


    func check_for_risk(
        order: MultipleOrder, size: felt, execution_price: felt
    ) {
    }

    func return_acc_value() -> (res: felt) {
    }

    func return_maintenance() -> (res: felt) {
    }
}
