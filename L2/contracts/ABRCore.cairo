%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from contracts.libraries.CommonLibrary import CommonLib
from contracts.Constants import STATE_0, STATE_1, STATE_2

// ///////////
// Storage //
// ///////////

// Version of Asset contract to refresh in node
@storage_var
func version() -> (res: felt) {
}

@storage_var
func state() -> (res: felt) {
}

@storage_var
func name() -> (res: felt) {
}

@storage_var
func current_timestamp() -> (res: felt) {
}

@storage_var
func abr_market_status(timestamp: felt, market_id: felt) -> (status: felt) {
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
}(current_abr_timestamp_: felt, markets_list_len_: felt, markets_list_: Market*) {
    if (markets_list_len_ == 0) {
        return 1;
    }

    let (market_status) = abr_market_status(
        timestamp=current_abr_timestamp_, market_id=[markets_list_].id
    );

    if (market_status == 0) {
        return 0;
    }

    check_abr_markets_status_recurse(
        current_abr_timestamp_=current_abr_timestamp_,
        markets_list_len_=markets_list_len_ - 1,
        markets_list_=markets_list_ + Market.SIZE,
    );
}

func check_abr_markets_status{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    current_abr_timestamp_: felt, markets_list_len_: felt, markets_list_: Market*
) {
    let (status) = check_abr_markets_status_recurse(
        markets_list_len_=markets_list_len_, markets_list_=markets_list_
    );

    if (status == 1) {
        state.write(value=STATE_2);
    }

    return ();
}

@external
func set_current_abr_timestamp{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_timestamp: felt
) {
    let (current_state) = state.read();
    let (last_timestamp) = current_timestamp.read();

    with_attr error_message("ABRCore: Invalid State") {
        assert current_state = STATE_0;
    }

    with_attr error_message("ABRCore: New Timstamp must be > last timestamp") {
        assert_lt(last_timestamp, new_timestamp);
    }

    state.write(value=STATE_1);
    current_timestamp.write(value=last_timestamp);
}

@external
func set_abr_value{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, perp_index_len: felt, perp_index: felt*, perp_mark_len: felt, perp_mark: felt*
) {
    let (current_state) = state.read();
    let (current_abr_timestamp) = current_timestamp.read();

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (abr_calculations_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_Calculations_INDEX, version=version
    );

    let (markets_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    let (market_details: Market) = IMarkets.get_market(
        contract_address=markets_address, market_id_=market_id_
    );

    with_attr error_message("ABRCore: Given Market is not tradable") {
        assert market_details.tradable = TRUE;
    }

    with_attr error_message("ABRCore: Invalid State") {
        assert current_state = STATE_1;
    }

    IABR_Calculations.calculate_abr(
        contract_address=abr_calculations_address,
        market_id_=market_id_,
        perp_index_len=perp_index_len,
        perp_index=perp_index,
        perp_mark_len=perp_mark_len,
        perp_mark=perp_mark,
    );

    let (markets_list_len_: felt, markets_list_: Market*) = IMarkets.get_all_markets_by_state(
        is_tradable_=TRUE, is_archived_=FALSE
    );

    check_abr_markets_status(
        current_abr_timestamp_=current_abr_timestamp,
        markets_list_len_=markets_list_len_,
        markets_list_=markets_list_,
    );
    return ();
}

@external
func make_abr_payments{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (current_state) = state.read();
    let (last_timestamp) = current_timestamp.read();

    with_attr error_message("ABRCore: Invalid State") {
        assert current_state = STATE_2;
    }

    let (abr_payments_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_PAYMENT_INDEX, version=version
    );

    IABR_Payment.pay_abr();

    // Change state
}
