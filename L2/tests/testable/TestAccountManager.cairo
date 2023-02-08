%lang starknet

// %builtins pedersen range_check ecdsa

from contracts.AccountManager import (
    constructor,
    get_public_key,
    is_valid_signature,
    is_valid_signature_order,
    get_balance,
    get_position_data,
    get_L1_address,
    get_deleveragable_or_liquidatable_position,
    get_positions_for_risk_management,
    get_portion_executed,
    return_array_collaterals,
    get_withdrawal_history,
    deposit,
    transfer_from,
    transfer_from_abr,
    transfer_abr,
    transfer,
    get_simplified_positions,
    get_positions,
    execute_order,
    update_withdrawal_history,
    withdraw,
    liquidate_position,
    order_hash_check,
    populate_withdrawals_array,
    populate_array_collaterals,
    populate_positions,
    populate_simplified_positions,
    populate_positions_risk_management,
    hash_order,
    hash_withdrawal_request,
    add_to_market_array,
    remove_from_market_array,
    add_collateral,
    find_index_to_be_updated_recurse,
    check_for_withdrawal_replay,
    balance,
    collateral_array_len,
    deleveragable_or_liquidatable_position,
)
from starkware.cairo.common.cairo_builtins import HashBuiltin

// ///////////
// External //
// ///////////

// #### TODO: Remove; Only for testing purposes #####
@external
func set_balance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    assetID_: felt, amount_: felt
) {
    let (curr_balance) = balance.read(assetID_);
    balance.write(assetID=assetID_, value=amount_);
    let (array_len) = collateral_array_len.read();

    if (curr_balance == 0) {
        add_collateral(new_asset_id=assetID_, iterator=0, length=array_len);
        return ();
    } else {
        return ();
    }
}
