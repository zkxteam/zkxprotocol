%lang starknet

// %builtins pedersen range_check ecdsa

from contracts.AccountManager import (
    constructor,
    get_public_key,
    is_valid_signature,
    is_valid_signature_order,
    get_balance,
    get_order_data,
    get_L1_address,
    get_amount_to_be_sold,
    get_deleveraged_or_liquidatable_position,
    return_array_positions,
    return_array_collaterals,
    get_withdrawal_history,
    timestamp_check,
    transfer_from,
    transfer_from_abr,
    transfer_abr,
    transfer,
    remove_from_array,
    execute_order,
    update_withdrawal_history,
    withdraw,
    liquidate_position,
    check_for_withdrawal_replay,
    find_index_to_be_updated_recurse,
    add_collateral,
    add_to_array,
    hash_withdrawal_request,
    hash_order,
    populate_array_positions,
    populate_array_collaterals,
    populate_withdrawals_array,
    balance,
    collateral_array_len,
)
from starkware.cairo.common.cairo_builtins import HashBuiltin

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
