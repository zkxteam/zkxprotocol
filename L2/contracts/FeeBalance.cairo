%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_nn
from starkware.starknet.common.syscalls import get_caller_address

from contracts.Constants import Trading_INDEX, MasterAdmin_ACTION
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_assert64x61

//##########
// Events  #
//##########

@event
func fee_mapping_updated(
    user_address: felt,
    assetID: felt,
    fee_to_add: felt,
    prev_user_fee_for_asset: felt,
    prev_asset_fee: felt,
) {
}

@event
func FeeBalance_withdraw_called(
    assetID: felt, amount_to_withdraw: felt, prev_total_asset_fee: felt
) {
}

//##########
// Storage #
//##########

// Stores <address, assetID> to fee mapping
@storage_var
func fee_mapping(address: felt, assetID: felt) -> (fee: felt) {
}

// Stores <assetID> to accumulated_fee mapping
@storage_var
func total_fee_per_asset(assetID: felt) -> (accumulated_fee: felt) {
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

// @notice Function to get the total fee accumulated in the system
// @param assetID_ - asset ID of the collateral
// @return fee - total fee in the system
@view
func get_total_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    assetID_: felt
) -> (fee: felt) {
    let (fee) = total_fee_per_asset.read(assetID=assetID_);
    return (fee,);
}

// @notice Function to get the total accumulated fee for a specific user
// @param address - address of the user for whom total fee is to be obtained
// @param assetID_ - asset ID of the collateral
// @return fee - total accumulated fee for the user
@view
func get_user_fee{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address: felt, assetID_: felt
) -> (fee: felt) {
    let (fee) = fee_mapping.read(address=address, assetID=assetID_);
    return (fee,);
}

//#####################
// External Functions #
//#####################

// @notice Function to update fee mapping which stores total fee for a user
// @param address - address of the user for whom fee is to be updated
// @param assetID_ - asset ID of the collateral
// @param fee_to_add_ - fee value that is to be added
@external
func update_fee_mapping{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address: felt, assetID_: felt, fee_to_add_: felt
) {
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    );

    with_attr error_message("Access is denied since caller is not trading contract") {
        assert caller = trading_address;
    }

    with_attr error_message("Fee to be added should be non negative") {
        assert_nn(fee_to_add_);
    }

    let current_fee: felt = fee_mapping.read(address=address, assetID=assetID_);
    let new_fee: felt = current_fee + fee_to_add_;

    with_attr error_message("New fee must be in 64x61 range") {
        Math64x61_assert64x61(new_fee);
    }

    fee_mapping.write(address=address, assetID=assetID_, value=new_fee);

    let current_total_fee_per_asset: felt = total_fee_per_asset.read(assetID=assetID_);
    let new_total_fee_per_asset: felt = current_total_fee_per_asset + fee_to_add_;

    with_attr error_message("Total fee must be in 64x61 range") {
        Math64x61_assert64x61(new_total_fee_per_asset);
    }

    total_fee_per_asset.write(assetID=assetID_, value=new_total_fee_per_asset);

    fee_mapping_updated.emit(
        user_address=address,
        assetID=assetID_,
        fee_to_add=fee_to_add_,
        prev_user_fee_for_asset=current_fee,
        prev_asset_fee=current_total_fee_per_asset,
    );

    return ();
}

// @notice Function to update fee mapping which stores total fee for a user
// @param address - address of the user for whom fee is to be updated
// @param assetID_ - asset ID of the collateral
// @param fee_to_withdraw_ - fee value that is to be added
@external
func withdraw{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    assetID_: felt, amount_to_withdraw_: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Auth check
    with_attr error_message("Caller is not Master Admin") {
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    with_attr error_message("Amount to be withdrawn should be greater than 0") {
        assert_lt(0, amount_to_withdraw_);
    }

    with_attr error_message("Amount should be in 64x61 representation") {
        Math64x61_assert64x61(amount_to_withdraw_);
    }

    let current_total_fee_per_asset: felt = total_fee_per_asset.read(assetID=assetID_);

    with_attr error_message("Amount to withdraw is more than balance available") {
        assert_le(amount_to_withdraw_, current_total_fee_per_asset);
    }

    let new_total_fee_per_asset: felt = current_total_fee_per_asset - amount_to_withdraw_;
    total_fee_per_asset.write(assetID=assetID_, value=new_total_fee_per_asset);

    FeeBalance_withdraw_called.emit(
        assetID=assetID_,
        amount_to_withdraw=amount_to_withdraw_,
        prev_total_asset_fee=current_total_fee_per_asset,
    );

    return ();
}
