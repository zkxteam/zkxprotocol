%lang starknet

from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_lt
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.UserBatches import calculate_no_of_batches, get_batch
from contracts.Constants import (
    STATE_0,
    STATE_1,
    STATE_2,
    ABR_PAYMENT_INDEX,
    ABR_Calculations_INDEX,
    AccountRegistry_INDEX,
    Market_INDEX,
)
from contracts.DataTypes import Market
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IABR_Calculations import IABR_Calculations
from contracts.interfaces.IABRPayment import IABRPayment
from contracts.interfaces.IMarkets import IMarkets

// ///////////
// Storage //
// ///////////

@storage_var
func state() -> (res: felt) {
}

@storage_var
func epoch() -> (epoch: felt) {
}

@storage_var
func epcoch_to_timestamp(epoch: felt) -> (timestamp: felt) {
}

@storage_var
func abr_market_status(epoch: felt, market_id: felt) -> (status: felt) {
}

@storage_var
func no_of_users_per_batch() -> (value: felt) {
}

@storage_var
func batches_fetched_for_epoch(epoch: felt) -> (batches_fetched: felt) {
}

@storage_var
func no_of_batches_for_epoch(epoch: felt) -> (no_of_batches: felt) {
}

// ///////////////
// Constructor //
// ///////////////

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

func check_abr_markets_status_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(current_epoch_: felt, markets_list_len_: felt, markets_list_: Market*) -> (res: felt) {
    if (markets_list_len_ == 0) {
        return (1,);
    }

    let (market_status) = abr_market_status.read(
        epoch=current_epoch_, market_id=[markets_list_].id
    );

    if (market_status == 0) {
        return (0,);
    }

    return check_abr_markets_status_recurse(
        current_epoch_=current_epoch_,
        markets_list_len_=markets_list_len_ - 1,
        markets_list_=markets_list_ + Market.SIZE,
    );
}

func check_abr_markets_status{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    current_epoch_: felt, markets_list_len_: felt, markets_list_: Market*
) {
    alloc_locals;
    let (status) = check_abr_markets_status_recurse(
        current_epoch_=current_epoch_,
        markets_list_len_=markets_list_len_,
        markets_list_=markets_list_,
    );

    if (status == 1) {
        state.write(value=STATE_2);
        return ();
    } else {
        return ();
    }
}

@external
func set_current_abr_timestamp{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_timestamp: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (current_state) = state.read();
    let (current_epoch) = epoch.read();
    let (last_timestamp) = epcoch_to_timestamp.read(epoch=current_epoch);

    with_attr error_message("ABRCore: Invalid State") {
        assert current_state = STATE_0;
    }

    with_attr error_message("ABRCore: New Timstamp must be > last timestamp") {
        assert_lt(last_timestamp, new_timestamp);
    }

    let new_epoch = current_epoch + 1;
    state.write(value=STATE_1);
    epoch.write(value=new_epoch);
    epcoch_to_timestamp.write(epoch=new_epoch, value=new_timestamp);

    // Get account Registry address
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    );

    let (current_no_of_users_per_batch) = no_of_users_per_batch.read();
    let (no_of_batches) = calculate_no_of_batches(
        current_no_of_users_per_batch_=current_no_of_users_per_batch,
        account_registry_address_=account_registry_address,
    );
    no_of_batches_for_epoch.write(epoch=new_epoch, value=no_of_batches);

    return ();
}

@external
func set_abr_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, perp_index_len: felt, perp_index: felt*, perp_mark_len: felt, perp_mark: felt*
) {
    alloc_locals;
    let (current_state) = state.read();
    let (current_epoch) = epoch.read();
    let (current_timestamp) = epcoch_to_timestamp.read(epoch=current_epoch);

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (market_status) = abr_market_status.read(epoch=current_epoch, market_id=market_id_);

    let (abr_calculations_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_Calculations_INDEX, version=version
    );

    let (local markets_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    let (market_details: Market) = IMarkets.get_market(
        contract_address=markets_address, market_id_=market_id_
    );

    with_attr error_message("ABRCore: Invalid State") {
        assert current_state = STATE_1;
    }

    with_attr error_message("ABRCore: Given Market is not tradable") {
        assert market_details.is_tradable = TRUE;
    }

    with_attr error_message("ABRCore: ABR already set for the market") {
        assert market_status = 0;
    }

    IABR_Calculations.calculate_abr(
        contract_address=abr_calculations_address,
        market_id_=market_id_,
        perp_index_len=perp_index_len,
        perp_index=perp_index,
        perp_mark_len=perp_mark_len,
        perp_mark=perp_mark,
        timestamp_=current_timestamp,
    );

    let (markets_list_len_: felt, markets_list_: Market*) = IMarkets.get_all_markets_by_state(
        contract_address=markets_address, is_tradable_=TRUE, is_archived_=FALSE
    );

    check_abr_markets_status(
        current_epoch_=current_epoch,
        markets_list_len_=markets_list_len_,
        markets_list_=markets_list_,
    );
    return ();
}

// @notice Function to get the current batch (reverts if it crosses the set number of batches)
// @returns users_list_len - Length of the user batch
// @returns users_list - Users batch
func get_current_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    current_epoch_: felt, account_registry_address_: felt
) -> (users_list_len: felt, users_list: felt*) {
    alloc_locals;

    // Current Index
    let (current_no_of_users_per_batch) = no_of_users_per_batch.read();
    let (batches_fetched) = batches_fetched_for_epoch.read(epoch=current_epoch_);
    let (no_of_batches) = no_of_batches_for_epoch.read(epoch=current_epoch_);

    let (users_list_len, users_list) = get_batch(
        batch_id=batches_fetched,
        no_of_users_per_batch=current_no_of_users_per_batch,
        account_registry_address=account_registry_address_,
    );

    let new_batches_fetched = batches_fetched + 1;
    batches_fetched_for_epoch.write(epoch=current_epoch_, value=batches_fetched + 1);

    if (new_batches_fetched == no_of_batches) {
        state.write(value=STATE_0);
        return (users_list_len, users_list);
    } else {
        return (users_list_len, users_list);
    }
}

@external
func make_abr_payments{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (current_state) = state.read();
    let (current_epoch) = epoch.read();
    let (current_timestamp) = epcoch_to_timestamp.read(epoch=current_epoch);

    with_attr error_message("ABRCore: Invalid State") {
        assert current_state = STATE_2;
    }

    // Get account Registry address
    let (account_registry_address: felt) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    );

    let (local abr_payments_address: felt) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_PAYMENT_INDEX, version=version
    );

    let (users_list_len: felt, users_list: felt*) = get_current_batch(
        current_epoch_=current_epoch, account_registry_address_=account_registry_address
    );

    IABRPayment.pay_abr(
        contract_address=abr_payments_address,
        account_addresses_len=users_list_len,
        account_addresses=users_list,
    );

    return ();
}
