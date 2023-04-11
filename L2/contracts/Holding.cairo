%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin

from contracts.Constants import Holding_INDEX, Trading_INDEX
from contracts.libraries.FundLibrary import balance, FundLib

// /////////
// Events //
// /////////

// Event emitted whenever fund() is called
@event
func fund_Holding_called(asset_id: felt, amount: felt) {
}

// Event emitted whenever defund() is called
@event
func defund_Holding_called(asset_id: felt, amount: felt) {
}

// Event emitted whenever deposit() is called
@event
func deposit_Holding_called(asset_id: felt, amount: felt) {
}

// Event emitted whenever withdraw() is called
@event
func withdraw_Holding_called(asset_id: felt, amount: felt) {
}

// //////////////
// Constructor //
// //////////////

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    FundLib.initialize(registry_address_, version_);
    return ();
}

// ///////////
// External //
// ///////////

// @notice Manually add amount to asset_id's balance
// @param asset_id_ - target asset_id
// @param amount_ - value to add to asset_id's balance
@external
func fund{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount_: felt
) {
    FundLib.fund_contract(asset_id_, amount_, Holding_INDEX);
    fund_Holding_called.emit(asset_id=asset_id_, amount=amount_);

    return ();
}

// @notice Manually deduct amount from asset_id's balance
// @param asset_id_ - target asset_id
// @param amount_ - value to deduct from asset_id's balance
@external
func defund{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount_: felt
) {
    FundLib.defund_contract(asset_id_, amount_, Holding_INDEX);
    defund_Holding_called.emit(asset_id=asset_id_, amount=amount_);

    return ();
}

// @notice Deposit amount for a asset_id by an order
// @parama asset_id_ - target asset_id
// @param amount_ - value to deduct from asset_id's balance
@external
func deposit{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount_: felt
) {
    FundLib.deposit_to_contract(asset_id_, amount_, Trading_INDEX);
    deposit_Holding_called.emit(asset_id=asset_id_, amount=amount_);

    return ();
}

// @notice Withdraw amount for a asset_id by an order
// @param asset_id_ - target asset_id
// @param amount_ - value to deduct from asset_id's balance
@external
func withdraw{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    asset_id_: felt, amount_: felt
) {
    FundLib.withdraw_from_contract(asset_id_, amount_, Trading_INDEX);
    withdraw_Holding_called.emit(asset_id=asset_id_, amount=amount_);

    return ();
}
