@contract_interface
namespace ITradingFeesAdmin:
    func update_fees(
        long_fees_mod: felt,
        short_fees_mod: felt
    ):
    end

    func update_tier_criteria(
        tier_level: felt,
        tier_criteria_new: Tier_Details
    ):
    end

    func update_trade_access(
        tier_level: felt,
        trade_access_new: Trade_Details
    ):
    end
):
end