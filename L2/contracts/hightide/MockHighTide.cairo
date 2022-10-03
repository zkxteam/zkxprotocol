%lang starknet

from contracts.DataTypes import TradingSeason
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_block_timestamp

@storage_var
func curr_season(season_id: felt) -> (season: TradingSeason) {
}

@storage_var
func curr_season_id() -> (season_id: felt) {
}

@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    let (current_timestamp) = get_block_timestamp();
    let season: TradingSeason = TradingSeason(
        start_timestamp=current_timestamp,
        end_timestamp=current_timestamp + 604800,
        num_trading_days=7,
    );

    curr_season_id.write(value=1);
    curr_season.write(season_id=1, value=season);
    return ();
}

@external
func get_current_season_id{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    season_id: felt
) {
    let (season_id: felt) = curr_season_id.read();
    return (season_id,);
}

@external
func get_season{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    season_id: felt
) -> (trading_season: TradingSeason) {
    let (season: TradingSeason) = curr_season.read(season_id=season_id);
    return (season,);
}
