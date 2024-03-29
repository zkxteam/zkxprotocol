%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.cairo.common.math_cmp import is_le, is_nn
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.messages import send_message_to_l1
from contracts.DataTypes import QuoteL1Message
from contracts.Constants import AccountRegistry_INDEX, MasterAdmin_ACTION
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.libraries.Utils import verify_caller_authority

const MESSAGE_WITHDRAW = 0;

// //////////
// Storage //
// //////////

// @notice Stores the contract version
@storage_var
func contract_version() -> (version: felt) {
}

// @notice Stores the address of Authorized Registry contract
@storage_var
func registry_address() -> (contract_address: felt) {
}

// @notice stores the address of L1 zkx contract
@storage_var
func L1_zkx_address() -> (res: felt) {
}

// Stores messages that can be consumed at L1
@storage_var
func L1_message_array(index: felt) -> (res: QuoteL1Message) {
}

// stores the maximum length of message array
@storage_var
func L1_message_array_max_length() -> (len: felt) {
}

// //////////////
// Constructor //
// //////////////

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt, max_len_: felt
) {
    registry_address.write(value=registry_address_);
    contract_version.write(value=version_);
    L1_message_array_max_length.write(value=max_len_);
    return ();
}

// ///////
// View //
// ///////

// @notice Function to get a message in an index
// @param index_ - index at which the message is to be read
// @return message - message at the corresponding index
@view
func get_message{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(index_: felt) -> (
    message: QuoteL1Message
) {
    let (message) = L1_message_array.read(index=index_);
    return (message=message);
}

// ///////////
// External //
// ///////////

// @notice set L1 zkx contract address function
// @param address - L1 zkx contract address as an argument
@external
func set_L1_zkx_address{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    l1_zkx_address: felt
) {
    // Auth check
    with_attr error_message("Caller is not authorized to set L1 ZKX address") {
        let (registry) = registry_address.read();
        let (version) = contract_version.read();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    L1_zkx_address.write(value=l1_zkx_address);
    return ();
}

// @notice set maximum length for message array
// @param length_ - maximum length for message array
@external
func set_max_length{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    length_: felt
) {
    // Auth check
    with_attr error_message("Caller is not authorized to set message max length") {
        let (registry) = registry_address.read();
        let (version) = contract_version.read();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    L1_message_array_max_length.write(value=length_);
    return ();
}

// @notice function to check conditions and add message to the array
// @param user_l1_address_ User's L1 wallet address
// @param ID of collateral for the requested withdrawal
// @param amount_ Amount to be withdrawn
// @param timestamp_ - Time at which user submitted withdrawal request
// @param L1_fee_amount_ - Gas fee in L1
// @param L1_fee_asset_id_ - ID of collateral used to pay L1 gas fee
@external
func check_and_add_message{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    user_l1_address_: felt,
    asset_id_: felt,
    amount_: felt,
    timestamp_: felt,
    L1_fee_amount_: felt,
    L1_fee_asset_id_: felt,
) -> (result: felt) {
    alloc_locals;
    let (registry) = registry_address.read();
    let (version) = contract_version.read();
    let (caller) = get_caller_address();

    // fetch account registry contract address
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    );
    // check whether caller is registered user
    let (present) = IAccountRegistry.is_registered_user(
        contract_address=account_registry_address, address_=caller
    );

    with_attr error_message("Called account contract is not registered") {
        assert_not_zero(present);
    }

    let (result) = add_message_recurse(
        user_l1_address_,
        asset_id_,
        amount_,
        timestamp_,
        L1_fee_amount_,
        L1_fee_asset_id_,
        arr_len_=0,
    );

    return (result=result);
}

// ///////////
// Internal //
// ///////////

// @notice Internal function to recursively find the index of the withdrawal request to be updated
// @param user_l1_address_ - User's L1 wallet address
// @param asset_id_ - collateral on which user submitted withdrawal request
// @param amount_ - Amount of funds that user has withdrawn
// @param timestamp_ - Time at which user submitted withdrawal request
// @param status_ - Status of the withdrawal request
// @param arr_len_ - current index which is being checked to be updated
func add_message_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    user_l1_address_: felt,
    asset_id_: felt,
    amount_: felt,
    timestamp_: felt,
    L1_fee_amount_: felt,
    L1_fee_asset_id_: felt,
    arr_len_: felt,
) -> (res: felt) {
    alloc_locals;

    let (message_array_max_length) = L1_message_array_max_length.read();
    if (arr_len_ == message_array_max_length) {
        return (0,);
    }

    let (message: QuoteL1Message) = L1_message_array.read(index=arr_len_);
    if (message.timestamp == 0) {
        let new_message = QuoteL1Message(
            user_l1_address=user_l1_address_,
            asset_id=asset_id_,
            amount=amount_,
            timestamp=timestamp_,
            L1_fee_amount=L1_fee_amount_,
            L1_fee_asset_id=L1_fee_asset_id_,
        );
        L1_message_array.write(index=arr_len_, value=new_message);
        return (1,);
    }

    let difference = timestamp_ - message.timestamp;
    let is_less = is_le(difference, 600);
    if (is_less == 0) {
        let new_message = QuoteL1Message(
            user_l1_address=user_l1_address_,
            asset_id=asset_id_,
            amount=amount_,
            timestamp=timestamp_,
            L1_fee_amount=L1_fee_amount_,
            L1_fee_asset_id=L1_fee_asset_id_,
        );
        L1_message_array.write(index=arr_len_, value=new_message);
        return (1,);
    }

    return add_message_recurse(
        user_l1_address_,
        asset_id_,
        amount_,
        timestamp_,
        L1_fee_amount_,
        L1_fee_asset_id_,
        arr_len_ + 1,
    );
}
