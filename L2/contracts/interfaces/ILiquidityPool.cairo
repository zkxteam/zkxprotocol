%lang starknet

from starkware.cairo.common.uint256 import Uint256

@contract_interface
namespace ILiquidityPool {
    // External functions

    func distribute_reward_tokens(
        trader_address_: felt, reward_amount_Uint256_: Uint256, l1_token_address_: felt
    ) {
    }

    func perform_return_or_burn() {
    }
}
