%lang starknet

from contracts.DataTypes import PriceData

@contract_interface
namespace ILiquidate:

    func check_liquidation(
    account_address : felt, prices_len : felt, prices : PriceData*
    ) -> (liq_result : felt, least_collateral_ratio_position : felt):
    end

end
