%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import unsigned_div_rem, assert_le, assert_in_range, assert_lt
from starkware.cairo.common.math_cmp import is_nn, is_le
from contracts.Math_64x61 import Math64x61_div, Math64x61_fromIntFelt
from contracts.libraries.CommonLibrary import (
    CommonLib,
    get_contract_version,
    get_registry_address,
    set_contract_version,
    set_registry_address,
)

//##############
// Constructor #
//##############

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    return ();
}

//#####################
// Internal Functions #
//#####################

func find_max_frequency{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    iterator: felt,
    pair_frequency: felt*,
    top_pair_frequency: felt*,
    pair_frequency_max_,
    top_pair_frequency_max_,
) -> (pair_frequency_max_: felt, top_pair_frequency_max_: felt) {
    alloc_locals;
    if (pair_frequency_len == 0) {
        return (pair_frequency_max_, top_pair_frequency_max_);
    }

    let is_larger_pair = is_le(pair_frequency_max_, [pair_frequency]);
    let is_larger_top_pair = is_le(top_pair_frequency_max_, [top_pair_frequency]);

    local pair_res;
    local top_pair_res;
    if (is_larger_pair == 1) {
        pair_res = [pair_frequency];
    } else {
        pair_res = pair_frequency_max_;
    }

    if (is_larger_top_pair == 1) {
        top_pair_res = [top_pair_frequency];
    } else {
        top_pair_res = top_pair_frequency_max_;
    }

    find_max_frequency(
        iterator - 1, pair_frequency + 1, top_pair_frequency + 1, pair_res, top_pair_res
    );
}

func calculate_x2{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, top_pair_id_, pair_id_: felt, trading_stats_address_: felt
) {
    let (
        pair_frequency_len: felt, pair_frequency: felt*
    ) = ITradingStats.get_season_trade_frequency(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=pair_id_
    );
    let (
        top_pair_frequency_len: felt, top_pair_frequency: felt*
    ) = ITradingStats.get_season_trade_frequency(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=top_pair_id_
    );

    with_attr error_message("Length mismatch of pair and top pair") {
        assert pair_frequency_len = top_pair_frequency_len;
    }

    let (pair_frequency_max: felt, top_pair_frequency_max) = find_max_frequency(
        pair_frequency, top_pair_frequency, pair_frequency_len, 0, 0
    );

    let (pair_frequency_max_64x61: felt) = Math64x61_fromIntFelt(pair_frequency_max);
    let (top_pair_frequency_max_64x61: felt) = Math64x61_fromIntFelt(top_pair_frequency_max);

    let (x2: felt) = Math64x61_div(pair_frequency_max_64x61, top_pair_frequency_max_64x61);

    return (x2,);
}

func calculate_x3{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, total_days_: felt, trading_stats_address_: felt
) {
    let (num_days_traded: felt) = ITradingStats.get_total_days_traded(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=pair_id_
    );

    let (num_days_traded_64x61: felt) = Math64x61_fromIntFelt(num_days_traded);
    let (total_days_64x61: felt) = Math64x61_fromIntFelt(total_days_);

    let (x3: felt) = Math64x61_div(num_days_traded_64x61, total_days_64x61);

    return (x3,);
}

func calculate_x4{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id_: felt, pair_id_: felt, top_pair_id_: felt, trading_stats_address_: felt
) {
    let (pair_number_of_traders: felt) = ITradingStats.get_num_active_traders(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=pair_id_
    );

    let (top_pair_number_of_traders: felt) = ITradingStats.get_num_active_traders(
        contract_address=trading_stats_address_, season_id_=season_id_, pair_id_=top_pair_id_
    );

    let (pair_number_of_traders_64x61: felt) = Math64x61_fromIntFelt(pair_number_of_traders);
    let (top_pair_number_of_traders_64x61: felt) = Math64x61_fromIntFelt(
        top_pair_number_of_traders
    );

    let (x3: felt) = Math64x61_div(pair_number_of_traders_64x61, top_pair_number_of_traders_64x61);

    return (x4,);
}
