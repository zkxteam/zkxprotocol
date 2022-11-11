%lang starknet

from contracts.DataTypes import TraderStats

@contract_interface
namespace IUserStats {
    // external functions
    func record_trader_stats(
        season_id: felt, pair_id: felt, trader_stats_list_len: felt, trader_stats_list: TraderStats*
    ) {
    }
}
