%lang starknet
from starkware.starknet.common.syscalls import get_caller_address
from contracts.DataTypes import HighTideMetaData
from contracts.Constants import HIGHTIDE_ACTIVE
from contracts.hightide.HighTide import (
    constructor,
    hightide_by_season_id,
    reward_tokens_len_by_hightide,
    hightide_rewards_by_id,
    hightide_by_id,
    hightides_array_len,
    seasons_array_len,
    liquidity_pool_contract_class_hash,
    constants_to_calculate_trader_score,
    multipliers_to_calculate_reward,
    trading_season_by_id,
    current_trading_season,
    get_current_season_id,
    get_season,
    get_hightide,
    get_multipliers,
    get_constants,
    get_hightide_reward_tokens,
    get_season_expiry_state,
    get_hightides_by_season_id,
    setup_trade_season,
    start_trade_season,
    end_trade_season,
    set_multipliers,
    set_constants,
    set_liquidity_pool_contract_class_hash,
    initialize_high_tide,
    verify_season_id_exists,
    verify_hightide_id_exists,
    validate_season_to_start,
    set_hightide_reward_tokens_recurse,
    populate_reward_tokens_recurse,
    deploy_liquidity_pool_contract,
    check_activation_recurse,
    verify_token_balance_recurse,
    assign_hightide_to_season,
    populate_hightide_list_recurse,
    previous_trading_season,
    market_under_hightide,
    is_market_under_hightide
)
from starkware.cairo.common.cairo_builtins import HashBuiltin

// @notice - This function is used to activate high tide
// @param hightide_id - id of hightide
@external
func activate_high_tide{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    hightide_id: felt
) {
    alloc_locals;
    verify_hightide_id_exists(hightide_id);

    let (hightide_metadata: HighTideMetaData) = get_hightide(hightide_id);
    // Update hightide status to active
    let hightide: HighTideMetaData = HighTideMetaData(
        market_id=hightide_metadata.market_id,
        status=HIGHTIDE_ACTIVE,
        season_id=hightide_metadata.season_id,
        token_lister_address=hightide_metadata.token_lister_address,
        is_burnable=hightide_metadata.is_burnable,
        liquidity_pool_address=hightide_metadata.liquidity_pool_address,
    );

    hightide_by_id.write(hightide_id, hightide);

    // Emit event
    let (caller) = get_caller_address();
    assign_hightide_to_season(hightide_id, hightide_metadata.season_id);

    market_under_hightide.write(hightide_metadata.season_id, hightide_metadata.market_id, 1);

    return ();
}
