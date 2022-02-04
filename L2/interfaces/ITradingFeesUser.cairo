@contract_interface
namespace ITradingFeesUser:
    func get_tier_criteria(
        tier_level: felt
    ) -> (
        tier_criteria_curr: Tier_Details
    ): 
    end

 
    func get_trade_access(
        tier_level: felt
    ) -> (
        trade_access_curr: Trade_Details
    ):
    end

    func get_fees(
    ) -> (
        long_fees: felt, 
        short_fees: felt
    ):
    end

end
