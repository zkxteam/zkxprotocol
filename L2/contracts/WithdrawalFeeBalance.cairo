%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_nn, assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address

from contracts.Constants import AccountRegistry_INDEX, Asset_INDEX, MasterAdmin_ACTION
from contracts.DataTypes import Asset
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_assert64x61

//#########
// Events #
//#########

// Event emitted whenever set_standard_withdraw_fee() is called
@event
func set_standard_withdraw_fee_called(fee: felt, collateral_id: felt) {
}

// Event emitted whenever update_withdrawal_fee_mapping() is called
@event
func update_withdrawal_fee_mapping_called(collateral_id: felt, fee_added: felt) {
}

// Event emitted whenever withdraw() is called
@event
func WithdrawalFeeBalance_withdraw_called(collateral_id: felt, fee_withdrawn: felt) {
}

//##########
// Storage #
//##########

// Stores the standard withdraw fee
@storage_var
func standard_withdraw_fee() -> (fee: felt) {
}

// Stores the standard withdraw fee collateral id
@storage_var
func standard_withdraw_fee_collateral_id() -> (collateral_id: felt) {
}

// Stores the total withdrawal fee per asset
@storage_var
func total_withdrawal_fee_per_asset(collateral_id: felt) -> (accumulated_fee: felt) {
}

//##############
// Constructor #
//##############

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

//#################
// View Functions #
//#################

// @notice Function to get the total withdrawal fee accumulated in the system
// @param collateral_id_ - collateral to be withdrawn
// @return fee - total withdrawal fee in the system
@view
func get_total_withdrawal_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    collateral_id_: felt
) -> (fee: felt) {
    let (fee) = total_withdrawal_fee_per_asset.read(collateral_id=collateral_id_);
    return (fee,);
}

// @notice Function to get standard withdraw fee
// @return fee, collateral_id - standard withdraw fee and fee represented in collateral_id
@view
func get_standard_withdraw_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    ) -> (fee: felt, collateral_id: felt) {
    let (fee) = standard_withdraw_fee.read();
    let (collateral_id) = standard_withdraw_fee_collateral_id.read();
    return (fee, collateral_id);
}

//#####################
// External Functions #
//#####################

// @notice set standard withdraw fee
// @param fee_ - 0.02 USDC is the standard withdraw fee
// @param collateral_id_ - Id of the standard withdrawal fee collateral
@external
func set_standard_withdraw_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    fee_: felt, collateral_id_: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message(
            "WithdrawalFeeBalance: Unauthorized call for withdset_standard_withdraw_fee") {
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    // Update standard fee
    with_attr error_message("WithdrawalFeeBalance: Fee should be non-negative") {
        assert_nn(fee_);
    }
    with_attr error_message("WithdrawalFeeBalance: Amount must be in 64x61 representation") {
        Math64x61_assert64x61(fee_);
    }
    standard_withdraw_fee.write(value=fee_);

    // Update standard collateral
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset: Asset) = IAsset.get_asset(contract_address=asset_address, id=collateral_id_);
    with_attr error_message("WithdrawalFeeBalance: Unregistered collateral passed") {
        assert_not_zero(asset.collateral);
    }
    standard_withdraw_fee_collateral_id.write(value=collateral_id_);

    // set_standard_withdraw_fee_called event is emitted
    set_standard_withdraw_fee_called.emit(fee=fee_, collateral_id=collateral_id_);

    return ();
}

// @notice Function to update withdrawal fee mapping which stores total fee for a user
// @param collateral_id_ - collateral to be withdrawn
// @param fee_to_add_ - withdrawal fee value that is to be added
@external
func update_withdrawal_fee_mapping{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    collateral_id_: felt, fee_to_add_: felt
) {
    // Auth check
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (caller) = get_caller_address();

    // fetch account registry contract address
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    );
    // check whether caller is registered user
    let (present) = IAccountRegistry.is_registered_user(
        contract_address=account_registry_address, address_=caller
    );

    with_attr error_message("WithdrawalFeeBalance: User address not registered") {
        assert_not_zero(present);
    }

    with_attr error_message("WithdrawalFeeBalance: Fee should be non-negative") {
        assert_nn(fee_to_add_);
    }

    with_attr error_message("WithdrawalFeeBalance: Amount must be in 64x61 representation") {
        Math64x61_assert64x61(fee_to_add_);
    }

    // Update Total withdrawal fee per asset
    let current_total_fee_per_asset: felt = total_withdrawal_fee_per_asset.read(
        collateral_id=collateral_id_
    );
    let new_total_fee_per_asset: felt = current_total_fee_per_asset + fee_to_add_;

    with_attr error_message("WithdrawalFeeBalance: Total fee must be in 64x61 representation") {
        Math64x61_assert64x61(new_total_fee_per_asset);
    }

    total_withdrawal_fee_per_asset.write(
        collateral_id=collateral_id_, value=new_total_fee_per_asset
    );

    // update_withdrawal_fee_mapping_called event is emitted
    update_withdrawal_fee_mapping_called.emit(collateral_id=collateral_id_, fee_added=fee_to_add_);

    return ();
}

// @notice Function to withdraw amount from this contract
// @param collateral_id_ - collateral to be withdrawn
// @param amount_to_withdraw_ - amount to be withdrawn
@external
func withdraw{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    collateral_id_: felt, amount_to_withdraw_: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("WithdrawalFeeBalance: Unauthorized call for withdraw") {
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    with_attr error_message("WithdrawalFeeBalance: Amount to withdraw should be non-zero") {
        assert_lt(0, amount_to_withdraw_);
    }

    with_attr error_message("WithdrawalFeeBalance: Amount must be in 64x61 representation") {
        Math64x61_assert64x61(amount_to_withdraw_);
    }

    // Update Total withdrawal fee per asset
    let current_total_fee_per_asset: felt = total_withdrawal_fee_per_asset.read(
        collateral_id=collateral_id_
    );
    with_attr error_message("WithdrawalFeeBalance: Insufficient balance to withdraw") {
        assert_le(amount_to_withdraw_, current_total_fee_per_asset);
    }
    let new_total_fee_per_asset: felt = current_total_fee_per_asset - amount_to_withdraw_;
    total_withdrawal_fee_per_asset.write(
        collateral_id=collateral_id_, value=new_total_fee_per_asset
    );

    // update_withdrawal_fee_mapping_called event is emitted
    WithdrawalFeeBalance_withdraw_called.emit(
        collateral_id=collateral_id_, fee_withdrawn=amount_to_withdraw_
    );

    return ();
}
