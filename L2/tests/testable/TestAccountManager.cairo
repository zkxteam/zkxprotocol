%lang starknet

// %builtins pedersen range_check ecdsa

from contracts.AccountManager import (
    constructor,
    get_public_key,
    get_account_deployed_block_number,
    is_valid_signature,
    is_valid_signature_order,
    get_balance,
    get_locked_margin,
    get_position_data,
    get_L1_address,
    get_deleveragable_or_liquidatable_position,
    get_portion_executed,
    get_safe_amount_to_withdraw,
    get_margin_info,
    get_account_info,
    return_array_collaterals,
    get_withdrawal_history,
    get_withdrawal_history_by_status,
    deposit,
    transfer_from,
    transfer_from_abr,
    transfer_abr,
    transfer,
    get_collateral_to_markets_array,
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
from contracts.Constants import MasterAdmin_ACTION
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from starkware.cairo.common.cairo_builtins import HashBuiltin


// ///////////
// External //
// ///////////

// #### TODO: Remove; Only for testing purposes #####
@external
func set_balance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    assetID_: felt, amount_: felt
) {
    with_attr error_message("TestAccountManager: Unauthorized Call") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

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
