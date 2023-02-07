%lang starknet

from contracts.DataTypes import BaseFee, Discount

@contract_interface
namespace ITradingFees {
    // external functions

    func update_base_fees(tier_: felt, fee_details: BaseFee) {
    }

    func update_discount(tier_: felt, discount_details: Discount) {
    }

    func update_max_base_fee_tier(tier_: felt) {
    }

    func update_max_discount_tier(tier_: felt) {
    }

    // view functions

    func get_base_fees(tier_: felt) -> (base_fee: BaseFee) {
    }

    func get_discount(tier_: felt) -> (discount: Discount) {
    }

    func get_max_base_fee_tier() -> (value: felt) {
    }

    func get_max_discount_tier() -> (value: felt) {
    }

    func get_discounted_fee_rate_for_user(address_: felt, side_: felt) -> (
        discounted_base_fee_percent: felt, base_fee_tier: felt, discount_tier: felt
    ) {
    }
}
