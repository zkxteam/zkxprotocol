%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_lt, assert_le
from starkware.starknet.common.syscalls import get_block_timestamp
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.UserBatches import calculate_no_of_batches, get_batch
from contracts.Constants import (
    ABR_STATE_0,
    ABR_STATE_1,
    ABR_STATE_2,
    ABR_PAYMENT_INDEX,
    ABR_Calculations_INDEX,
    AccountRegistry_INDEX,
    Market_INDEX,
    MasterAdmin_ACTION,
)

from contracts.DataTypes import Market
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IABRCalculations import IABRCalculations
from contracts.interfaces.IABRPayment import IABRPayment
from contracts.interfaces.IMarkets import IMarkets
from contracts.libraries.Utils import verify_caller_authority

// ////////////
// Constants //
// ////////////

const HOURS_8 = 28800;

// //////////
// Events //
// //////////

// Event emitted whenever collateral is transferred from account by trading
@event
func state_changed(epoch: felt, new_state: felt) {
}

@event
func abr_timestamp_set(epoch: felt, new_timestamp: felt) {
}

@event
func abr_set(epoch: felt, market_id: felt, abr_value: felt, abr_last_price: felt) {
}

@event
func abr_payment_made(epoch: felt, batch_id: felt) {
}

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
func epoch_market_to_abr_value(epoch: felt, market_id: felt) -> (abr_value: felt) {
}

@storage_var
func epoch_market_to_last_price(epoch: felt, market_id: felt) -> (last_price: felt) {
}

@storage_var
func epoch_to_timestamp(epoch: felt) -> (timestamp: felt) {
}

@storage_var
func abr_interval() -> (res: felt) {
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

@storage_var
func base_abr_rate() -> (value: felt) {
}

@storage_var
func bollinger_width() -> (value: felt) {
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
    let (block_timestamp) = get_block_timestamp();
    // initialize epoch 0 with timestamp at deployment
    epoch_to_timestamp.write(epoch=0, value=block_timestamp);
    // 8 hours
    abr_interval.write(value=28800);
    // 0.0000125 in 64x61
    base_abr_rate.write(value=28823037615171);
    // 2.0 in 64x61
    bollinger_width.write(value=4611686018427387904);
    return ();
}

// ////////
// View //
// ////////

// @notice View function to get the current state of the ABRCore contract
// @returns res - Current state
@view
func get_state{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (res: felt) {
    let (current_state) = state.read();
    return (current_state,);
}

// @notice View function to get the current epoch of the ABRCore contract
// @returns res - Current epoch
@view
func get_epoch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (res: felt) {
    let (current_epoch) = epoch.read();
    return (current_epoch,);
}

// @notice View function to get the current bollinger band width
// @returns res - boll_width
@view
func get_bollinger_width{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (boll_width) = bollinger_width.read();
    return (boll_width,);
}

// @notice View function to get the current base abr rate
// @returns res - base_abr
@view
func get_base_abr_rate{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (base_abr) = base_abr_rate.read();
    return (base_abr,);
}

// @notice View function to get the current interval of an ABR epoch
// @returns res - Current epoch
@view
func get_abr_interval{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (current_abr_interval) = abr_interval.read();
    return (current_abr_interval,);
}

// @notice View function that returns the list of markets for which the abr value is not set
// @returns remaining_markets_list_len - Length of the remaining markets array
// @returns remaining_markets_list - Remaining markets array
@view
func get_markets_remaining{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    remaining_markets_list_len: felt, remaining_markets_list: felt*
) {
    alloc_locals;
    // Get the registry and version
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get current state and alloc
    let (current_state) = state.read();
    let (current_epoch) = epoch.read();
    let (remaining_markets_list: felt*) = alloc();

    // Get hthe markets contract address from Auth Registry
    let (markets_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get all tradable markets in the system
    let (markets_list_len: felt, markets_list: Market*) = IMarkets.get_all_markets_by_state(
        contract_address=markets_address, is_tradable_=TRUE, is_archived_=FALSE
    );

    // Return the list of markets for which the abr value is not set
    if (current_state == ABR_STATE_1) {
        return populate_remaining_markets(
            current_epoch_=current_epoch,
            remaining_markets_list_len_=0,
            remaining_markets_list_=remaining_markets_list,
            markets_list_len_=markets_list_len,
            markets_list_=markets_list,
        );
    } else {
        return (0, markets_list);
    }
}

// @notice View function that returns the number of batches in the current epoch
// @returns res- Number of batches
@view
func get_no_of_batches_for_current_epoch{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}() -> (res: felt) {
    // Get the current state and epoch
    let (current_state) = state.read();
    let (current_epoch) = epoch.read();

    // Return number_of_batches if in state 2
    if (current_state == ABR_STATE_2) {
        let (no_of_batches) = no_of_batches_for_epoch.read(epoch=current_epoch);
        return (no_of_batches,);
    } else {
        return (0,);
    }
}

// @notice View function that returns the number of users in a batch
// @returns res - Number of users in a batch
@view
func get_no_of_users_per_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    ) -> (res: felt) {
    let (current_no_of_users_per_batch) = no_of_users_per_batch.read();
    return (current_no_of_users_per_batch,);
}

// @notice View function that returns the number of pay abr calls remaining to be executed
// @returns res- remaining calls
@view
func get_remaining_pay_abr_calls{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    ) -> (res: felt) {
    // Get current state and epoch
    let (current_state) = state.read();
    let (current_epoch) = epoch.read();

    // Get the no of batches and batches fetched
    let (no_of_batches) = no_of_batches_for_epoch.read(epoch=current_epoch);
    let (batches_fetched) = batches_fetched_for_epoch.read(epoch=current_epoch);

    if (current_state == ABR_STATE_2) {
        let remaining_batches = no_of_batches - batches_fetched;
        return (remaining_batches,);
    } else {
        return (0,);
    }
}

// @notice View function that returns the timestamp at which the next abr call is to be made
// @return res- timestamp
@view
func get_next_abr_timestamp{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (current_epoch) = epoch.read();
    let (current_abr_interval) = abr_interval.read();
    let (last_timestamp) = epoch_to_timestamp.read(epoch=current_epoch);
    let next_timestamp = last_timestamp + current_abr_interval;
    return (next_timestamp,);
}

// @notice View function that returns the abr_value and price
// @epoch epoch_
// @param market_id_
// @returns abr_value - ABR value of the given market in the epoch
// @returns price - Last price of the given market in the epoch
@view
func get_abr_details{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    epoch_: felt, market_id_: felt
) -> (abr_value: felt, abr_last_price: felt) {
    let (abr_value: felt) = epoch_market_to_abr_value.read(epoch=epoch_, market_id=market_id_);
    let (abr_last_price: felt) = epoch_market_to_last_price.read(
        epoch=epoch_, market_id=market_id_
    );
    return (abr_value, abr_last_price);
}

// ///////////
// External //
// ///////////

// @notice Function to set the abr interval
// @param new_abr_interval_ - New value for abr_interval
@external
func set_abr_interval{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_abr_interval_: felt
) {
    with_attr error_message("ABRCore: Unauthorized Call") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    with_attr error_message("ABRCore: new_abr_interval must be > 1800") {
        assert_le(1800, new_abr_interval_);
    }

    abr_interval.write(value=new_abr_interval_);

    return ();
}

// @notice - Base ABR value to be set by the admin
// @param new_base_abr_ - New base abr value
@external
func set_base_abr_rate{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_base_abr_: felt
) {
    with_attr error_message("ABRCore: Unauthorized Call") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    base_abr_rate.write(new_base_abr_);
    return ();
}

// @notice - Base bollinger width to be set by the admin
// @param new_base_abr_ - New bollinger width
@external
func set_bollinger_width{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_bollinger_width_: felt
) {
    with_attr error_message("ABRCore: Unauthorized Call") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    if (new_bollinger_width_ == 2) {
    }

    bollinger_width.write(new_bollinger_width_);
    return ();
}

// @notice Function to set the number of users in a batch; callable by masteradmin
// @param new_no_of_users_per_batch
@external
func set_no_of_users_per_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_no_of_users_per_batch
) {
    with_attr error_message("ABRCore: Unauthorized Call") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    with_attr error_message("ABRCore: No of users in a batch must be > 0") {
        assert_lt(0, new_no_of_users_per_batch);
    }
    no_of_users_per_batch.write(new_no_of_users_per_batch);
    return ();
}

// @notice Function to set the current abr_timestamp
// @requirements - Contract must be in state 0
// @param new_timestmap - New ABR timestmap
@external
func set_abr_timestamp{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_timestamp: felt
) {
    // Get registry and version
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get current state and epoch
    let (current_state) = state.read();
    let (current_epoch) = epoch.read();
    let (current_abr_interval) = abr_interval.read();

    // Get last epoch's timestamp
    let (last_timestamp) = epoch_to_timestamp.read(epoch=current_epoch);

    // Contract must be in state 0
    with_attr error_message("ABRCore: Invalid State") {
        assert current_state = ABR_STATE_0;
    }

    // Enforces last_abr_timestamp + abr_interval < new_timestamp
    with_attr error_message("ABRCore: New Timstamp must be > last timestamp + abr_interval") {
        assert_le(last_timestamp + current_abr_interval, new_timestamp);
    }

    // New epoch
    let new_epoch = current_epoch + 1;

    // Write to state
    state.write(value=ABR_STATE_1);
    epoch.write(value=new_epoch);
    epoch_to_timestamp.write(epoch=new_epoch, value=new_timestamp);

    // Get account Registry address
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    );

    // Get no of users in a batch
    let (current_no_of_users_per_batch) = no_of_users_per_batch.read();

    // Get the no of batches
    let (no_of_batches) = calculate_no_of_batches(
        current_no_of_users_per_batch_=current_no_of_users_per_batch,
        account_registry_address_=account_registry_address,
    );

    // Write the no of batches for this epoch
    no_of_batches_for_epoch.write(epoch=new_epoch, value=no_of_batches);

    // emit events
    abr_timestamp_set.emit(epoch=new_epoch, new_timestamp=new_timestamp);
    state_changed.emit(epoch=new_epoch, new_state=ABR_STATE_1);

    return ();
}

// @notice Function to set the abr for a market
// @requirements - Contract must be in state 1
// @param market_id_ - Market Id for which the abr value is to be set
// @param perp_index_len - Length of the perp_index array
// @param perp_index - Perp Index array
// @param perp_mark_len - Length of the perp_mark array
// @param perp_mark - Perp Marke array
@external
func set_abr_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, perp_index_len: felt, perp_index: felt*, perp_mark_len: felt, perp_mark: felt*
) {
    alloc_locals;

    // Get current state, epoch and timestamp
    let (current_state) = state.read();
    let (current_epoch) = epoch.read();
    let (current_timestamp) = epoch_to_timestamp.read(epoch=current_epoch);

    // Get registry and version
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get market status
    let (market_status) = abr_market_status.read(epoch=current_epoch, market_id=market_id_);

    // Get ABR calculation address
    let (abr_calculations_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_Calculations_INDEX, version=version
    );

    // Get Market address
    let (local markets_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get Market details
    let (market_details: Market) = IMarkets.get_market(
        contract_address=markets_address, market_id_=market_id_
    );

    // ABRCore must be in State_1
    with_attr error_message("ABRCore: Invalid State") {
        assert current_state = ABR_STATE_1;
    }

    // Market must be tradable
    with_attr error_message("ABRCore: Given Market is not tradable") {
        assert market_details.is_tradable = TRUE;
    }

    // Check if the market's abr is already set
    with_attr error_message("ABRCore: ABR already set for the market") {
        assert market_status = FALSE;
    }

    // Get the boll_width and base_abr
    let (boll_width) = bollinger_width.read();
    let (base_abr) = base_abr_rate.read();

    // Calculate abr from the inputs
    let (abr_value: felt, abr_last_price: felt) = IABRCalculations.calculate_abr(
        contract_address=abr_calculations_address,
        perp_index_len=perp_index_len,
        perp_index=perp_index,
        perp_mark_len=perp_mark_len,
        perp_mark=perp_mark,
        boll_width_=boll_width,
        base_abr_=base_abr,
    );

    // Get all the tradable markets in the system
    let (markets_list_len_: felt, markets_list_: Market*) = IMarkets.get_all_markets_by_state(
        contract_address=markets_address, is_tradable_=TRUE, is_archived_=FALSE
    );

    // Set the market as set
    abr_market_status.write(epoch=current_epoch, market_id=market_id_, value=TRUE);
    epoch_market_to_abr_value.write(epoch=current_epoch, market_id=market_id_, value=abr_value);
    epoch_market_to_last_price.write(
        epoch=current_epoch, market_id=market_id_, value=abr_last_price
    );

    // emit events
    abr_set.emit(
        epoch=current_epoch,
        market_id=market_id_,
        abr_value=abr_value,
        abr_last_price=abr_last_price,
    );

    // Check if all markets are set, if yes change the state
    check_abr_markets_status(
        current_epoch_=current_epoch,
        markets_list_len_=markets_list_len_,
        markets_list_=markets_list_,
    );

    return ();
}

// @notice Function to make abr payments between users
// @requirements - Contract must be in state 2
@external
func make_abr_payments{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (current_state) = state.read();
    let (current_epoch) = epoch.read();
    let (current_timestamp) = epoch_to_timestamp.read(epoch=current_epoch);

    with_attr error_message("ABRCore: Invalid State") {
        assert current_state = ABR_STATE_2;
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
        epoch_=current_epoch,
        account_addresses_len=users_list_len,
        account_addresses=users_list,
        timestamp_=current_timestamp,
    );

    return ();
}

// ///////////
// Internal //
// ///////////

// @notice Recursive function to make a list of markets for which the abr is not set
// @param current_epoch_ - Current epoch of the ABR Core contract
// @param remaining_markets_list_len_ - Length of the new array
// @param remaining_markets_list_ - New array of remaining markets
// @param markets_list_len_ - Length of all the tradable markets array
// @param markets_list_ - Tradable markets array
// @returns remaining_markets_list_len - Length of the new remaining markets array
// @returns remaining_markets_list - New remaining array
func populate_remaining_markets{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    current_epoch_: felt,
    remaining_markets_list_len_: felt,
    remaining_markets_list_: felt*,
    markets_list_len_: felt,
    markets_list_: Market*,
) -> (remaining_markets_list_len: felt, remaining_markets_list: felt*) {
    // base condition
    if (markets_list_len_ == 0) {
        return (remaining_markets_list_len_, remaining_markets_list_);
    }

    // Get the market status; i.e if the abr value is set or not
    let (market_status) = abr_market_status.read(
        epoch=current_epoch_, market_id=[markets_list_].id
    );

    // If the abr_value is not set
    if (market_status == FALSE) {
        // Add it to the array
        assert remaining_markets_list_[remaining_markets_list_len_] = [markets_list_].id;

        // Call the next market
        return populate_remaining_markets(
            current_epoch_=current_epoch_,
            remaining_markets_list_len_=remaining_markets_list_len_ + 1,
            remaining_markets_list_=remaining_markets_list_,
            markets_list_len_=markets_list_len_ - 1,
            markets_list_=markets_list_ + Market.SIZE,
        );
    }

    // Call the next market
    return populate_remaining_markets(
        current_epoch_=current_epoch_,
        remaining_markets_list_len_=remaining_markets_list_len_,
        remaining_markets_list_=remaining_markets_list_,
        markets_list_len_=markets_list_len_ - 1,
        markets_list_=markets_list_ + Market.SIZE,
    );
}

// @notice Recursive function that return TRUE if all the market's abr value is set
// @param current_epoch_ - Current epoch of the ABRCore contract
// @param markets_list_len_ - Length of markets array
// @param markets_list_ - Markets array
// @returns res - 1 if all markets are set, 0 if one of them is not set
func check_abr_markets_status_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(current_epoch_: felt, markets_list_len_: felt, markets_list_: Market*) -> (res: felt) {
    if (markets_list_len_ == FALSE) {
        return (TRUE,);
    }

    let (market_status) = abr_market_status.read(
        epoch=current_epoch_, market_id=[markets_list_].id
    );

    if (market_status == FALSE) {
        return (FALSE,);
    }

    return check_abr_markets_status_recurse(
        current_epoch_=current_epoch_,
        markets_list_len_=markets_list_len_ - 1,
        markets_list_=markets_list_ + Market.SIZE,
    );
}

// @notice Function that increments the state if all the markets are set
// @param current_epoch_ - Current epoch of the ABRCore contract
// @param markets_list_len_ - Length of markets array
// @param markets_list_ - Markets array
func check_abr_markets_status{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    current_epoch_: felt, markets_list_len_: felt, markets_list_: Market*
) {
    alloc_locals;
    let (status) = check_abr_markets_status_recurse(
        current_epoch_=current_epoch_,
        markets_list_len_=markets_list_len_,
        markets_list_=markets_list_,
    );

    // Increment the state if all markets are set
    if (status == TRUE) {
        state_changed.emit(epoch=current_epoch_, new_state=ABR_STATE_2);
        state.write(value=ABR_STATE_2);
        return ();
    } else {
        return ();
    }
}

// @notice Function to get the current batch (reverts if it crosses the set number of batches)
// @param current_epoch_ - Current epoch of ABRCore
// @param account_registry_address_ - Address of the account registry
// @returns users_list_len - Length of the user batch
// @returns users_list - Users batch
func get_current_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    current_epoch_: felt, account_registry_address_: felt
) -> (users_list_len: felt, users_list: felt*) {
    alloc_locals;

    // Get the current batch details
    let (current_no_of_users_per_batch) = no_of_users_per_batch.read();
    let (batches_fetched) = batches_fetched_for_epoch.read(epoch=current_epoch_);
    let (no_of_batches) = no_of_batches_for_epoch.read(epoch=current_epoch_);

    // Get the current batch
    let (users_list_len: felt, users_list: felt*) = get_batch(
        batch_id=batches_fetched,
        no_of_users_per_batch=current_no_of_users_per_batch,
        account_registry_address=account_registry_address_,
    );

    // Increment batches_fetched
    let new_batches_fetched = batches_fetched + 1;
    batches_fetched_for_epoch.write(epoch=current_epoch_, value=new_batches_fetched);

    abr_payment_made.emit(epoch=current_epoch_, batch_id=batches_fetched);

    // If all batches are fetched, increment state
    if (new_batches_fetched == no_of_batches) {
        state_changed.emit(epoch=current_epoch_, new_state=ABR_STATE_0);
        state.write(value=ABR_STATE_0);
        return (users_list_len, users_list);
    } else {
        return (users_list_len, users_list);
    }
}
