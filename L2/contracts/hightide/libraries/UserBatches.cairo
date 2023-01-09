%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.interfaces.ITradingStats import ITradingStats
from starkware.cairo.common.math import unsigned_div_rem

// Function to calculate the number of batches given the no_of_users_per_batch
// @param season_id_ - id of the season
// @param market_id_ - id of the market pair
// @param current_no_of_users_per_batch_ - Number of users in a batch
// @param trading_stats_address_ - Trading Stats address
// @return no_of_batches - returns no.of batches
@view
func calculate_no_of_batches{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    market_id_: felt,
    current_no_of_users_per_batch_: felt,
    trading_stats_address_: felt,
) -> (no_of_batches: felt) {
    alloc_locals;

    local no_of_batches;
    // Get number of active traders for a market in a season
    let (local current_num_traders) = ITradingStats.get_num_active_traders(
        contract_address=trading_stats_address_, season_id_=season_id_, market_id_=market_id_
    );

    let (q, r) = unsigned_div_rem(current_num_traders, current_no_of_users_per_batch_);

    if (r == 0) {
        assert no_of_batches = q;
    } else {
        assert no_of_batches = q + 1;
    }

    return (no_of_batches,);
}

// Function to fetch the corresponding batch given the batch id
// @param season_id_ - id of the season
// @param market_id_ - id of the market pair
// @param batch_id - Batch id of the batch
// @param no_of_users_per_batch - Number of users in a batch
// @param trading_stats_address_ - Trading Stats address
@view
func get_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt,
    market_id_: felt,
    batch_id_: felt,
    no_of_users_per_batch_: felt,
    trading_stats_address_: felt,
) -> (trader_list_len: felt, trader_list: felt*) {
    // Get the lower index of the batch
    let lower_limit: felt = batch_id_ * no_of_users_per_batch_;
    // Get the upper index of the batch
    let upper_limit: felt = lower_limit + no_of_users_per_batch_;

    // Fetch the required batch from TradingStats
    let (trader_list_len: felt, trader_list: felt*) = ITradingStats.get_batch(
        contract_address=trading_stats_address_,
        season_id_=season_id_,
        market_id_=market_id_,
        starting_index_=lower_limit,
        ending_index_=upper_limit,
    );

    return (trader_list_len, trader_list);
}
