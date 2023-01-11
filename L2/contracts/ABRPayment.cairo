%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math import abs_value, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import get_caller_address
from contracts.Math_64x61 import Math64x61_mul
from contracts.Constants import (
    ABR_Core_Index,
    ABR_FUNDS_INDEX,
    ABR_Calculations_INDEX,
    AccountRegistry_INDEX,
    Market_INDEX,
    SHORT,
)

from contracts.DataTypes import SimplifiedPosition
from contracts.interfaces.IABR_Calculations import IABR_Calculations
from contracts.interfaces.IABRFund import IABRFund
from contracts.interfaces.IAccountManager import IAccountManager
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IMarkets import IMarkets
from contracts.libraries.CommonLibrary import CommonLib

// //////////
// Events //
// //////////

// Event emitted when abr payment called for a position
@event
func abr_payment_called_user_position(
    market_id: felt, direction: felt, account_address: felt, timestamp: felt
) {
}

// ///////////////
// Constructor //
// ///////////////

// @notice
// @param registry_address_ - Address of the auth registry
// @param contract_version_ Version of the contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, contract_version_: felt
) {
    CommonLib.initialize(registry_address_, contract_version_);
    return ();
}

// //////////////////////
// External Functions //
// //////////////////////

// @notice Function to be called by the node
// @param account_addresses_len_ - Length of the account_addresses array being passed
// @param account_addresses_ - Account addresses array
@external
func pay_abr{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_addresses_len: felt, account_addresses: felt*, timestamp_: felt
) {
    // Make sure that the caller is the authorized ABR Core contracts
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (ABR_core_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_Core_Index, version=version
    );

    with_attr error_message("ABRCalculations: Unauthorized call") {
        assert caller = ABR_core_address;
    }

    // Get the market smart-contract
    let (market_contract) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );

    // Get the ABR smart-contract
    let (abr_contract) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_Calculations_INDEX, version=version
    );
    // Get the ABR-funding smart-contract
    let (abr_funding_contract) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_FUNDS_INDEX, version=version
    );
    return pay_abr_users(
        account_addresses_len,
        account_addresses,
        market_contract,
        abr_contract,
        abr_funding_contract,
        timestamp_,
    );
}

// //////////////////////
// Internal Functions //
// //////////////////////

// @notice Internal function called by pay_abr_users_positions to transfer funds between ABR Fund and users
// @param account_address_ - Address of the user of whom the positions are passed
// @param abr_funding_ - Address of the ABR Fund contract
// @param collateral_id_ - Collateral id of the position
// @param market_id_ - Market id of the position
// @param abs_payment_amount_ - Absolute value of ABR payment
func user_pays{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_address_: felt,
    abr_funding_: felt,
    collateral_id_: felt,
    market_id_: felt,
    abs_payment_amount_: felt,
) {
    IAccountManager.transfer_from_abr(
        contract_address=account_address_,
        collateral_id_=collateral_id_,
        market_id_=market_id_,
        amount_=abs_payment_amount_,
    );
    IABRFund.deposit(
        contract_address=abr_funding_,
        account_address_=account_address_,
        market_id_=market_id_,
        amount_=abs_payment_amount_,
    );
    return ();
}

// @notice Internal function called by pay_abr_users_positions to transfer funds between ABR Fund and users
// @param account_address_ - Address of the user of whom the positions are passed
// @param abr_funding_ - Address of the ABR Fund contract
// @param collateral_id_ - Collateral id of the position
// @param market_id_ - Market id of the position
// @param abs_payment_amount_ - Absolute value of ABR payment
func user_receives{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_address_: felt,
    abr_funding_: felt,
    collateral_id_: felt,
    market_id_: felt,
    abs_payment_amount_: felt,
) {
    IABRFund.withdraw(
        contract_address=abr_funding_,
        account_address_=account_address_,
        market_id_=market_id_,
        amount_=abs_payment_amount_,
    );
    IAccountManager.transfer_abr(
        contract_address=account_address_,
        collateral_id_=collateral_id_,
        market_id_=market_id_,
        amount_=abs_payment_amount_,
    );
    return ();
}

// @notice Internal function called by pay_abr_users to iterate throught the positions of the account
// @param account_address - Address of the user of whom the positions are passed
// @param positions_len_ - Length of the positions array of the user
// @param positions_ - Positions array of the user
// @param market_contract_ - Address of the Market contract
// @param abr_contract_ - Address of the ABR contract
// @param abr_funding_contract_ - Address of the ABR Funding contract
func pay_abr_users_positions{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_address_: felt,
    positions_len_: felt,
    positions_: SimplifiedPosition*,
    market_contract_: felt,
    abr_contract_: felt,
    abr_funding_: felt,
    timestamp_: felt,
) {
    alloc_locals;

    if (positions_len_ == 0) {
        return ();
    }

    // Get the collateral ID of the market
    let (_, collateral_id) = IMarkets.get_asset_collateral_from_market(
        contract_address=market_contract_, market_id_=[positions_].market_id
    );

    // Get the abr value
    let (abr: felt, price: felt) = IABR_Calculations.get_abr_value(
        contract_address=abr_contract_, market_id=[positions_].market_id
    );

    // Find if the abr_rate is +ve or -ve
    let (position_value) = Math64x61_mul(price, [positions_].position_size);
    let (payment_amount) = Math64x61_mul(abr, position_value);
    let is_negative = is_le(abr, 0);

    // If the abr is negative
    if (is_negative == TRUE) {
        if ([positions_].direction == SHORT) {
            // user pays
            user_pays(
                account_address_,
                abr_funding_,
                collateral_id,
                [positions_].market_id,
                payment_amount,
            );
        } else {
            // user receives
            user_receives(
                account_address_,
                abr_funding_,
                collateral_id,
                [positions_].market_id,
                payment_amount,
            );
        }
        // If the abr is positive
    } else {
        if ([positions_].direction == SHORT) {
            // user receives
            user_receives(
                account_address_,
                abr_funding_,
                collateral_id,
                [positions_].market_id,
                payment_amount,
            );
        } else {
            // user pays
            user_pays(
                account_address_,
                abr_funding_,
                collateral_id,
                [positions_].market_id,
                payment_amount,
            );
        }
    }

    abr_payment_called_user_position.emit(
        market_id=[positions_].market_id,
        direction=[positions_].direction,
        account_address=account_address_,
        timestamp=timestamp_,
    );
    return pay_abr_users_positions(
        account_address_,
        positions_len_ - 1,
        positions_ + SimplifiedPosition.SIZE,
        market_contract_,
        abr_contract_,
        abr_funding_,
        timestamp_,
    );
}

// @notice Internal function called by pay_abr to iterate throught the account_addresses array
// @param account_addresses_len_ - Length of thee account_addresses array being passed
// @param account_addresses_ - Account addresses array
// @param account_registry_ - Address of the Account Registry contract
// @param market_contract_ - Address of the Market contract
// @param abr_contract_ - Address of the ABR contract
// @param abr_funding_contract_ - Address of the ABR Funding contract
func pay_abr_users{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    account_addresses_len_: felt,
    account_addresses_: felt*,
    market_contract_: felt,
    abr_contract_: felt,
    abr_funding_contract_: felt,
    timestamp_: felt,
) {
    if (account_addresses_len_ == 0) {
        return ();
    }

    // Get all the open positions of the user
    let (
        positions_len: felt, positions: SimplifiedPosition*
    ) = IAccountManager.get_simplified_positions(
        contract_address=[account_addresses_], timestamp_filter_=timestamp_
    );

    // Do abr payments for each position
    pay_abr_users_positions(
        [account_addresses_],
        positions_len,
        positions,
        market_contract_,
        abr_contract_,
        abr_funding_contract_,
        timestamp_,
    );

    return pay_abr_users(
        account_addresses_len_ - 1,
        account_addresses_ + 1,
        market_contract_,
        abr_contract_,
        abr_funding_contract_,
        timestamp_,
    );
}
