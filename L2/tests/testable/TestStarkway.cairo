%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_in_range, assert_not_zero
from starkware.cairo.common.uint256 import Uint256
from starkware.starknet.common.syscalls import deploy

from contracts.Constants import MasterAdmin_ACTION
from contracts.interfaces.IERC20 import IERC20
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority

// //////////
// Storage //
// //////////

// Mapping to store number of whitelisted token addresses for a particular token
@storage_var
func whitelisted_token_l2_address_length(l1_address: felt) -> (number_of_whitelisted_tokens: felt) {
}

// Mapping to store all whitelisted L2 ERC-20 contract addresses of a particular token
@storage_var
func whitelisted_token_l2_address(l1_address: felt, index: felt) -> (l2_address: felt) {
}

// Mapping to store native L2 token address for a specific L1 ERC-20 contract address
@storage_var
func native_token_l2_address(l1_address: felt) -> (l2_address: felt) {
}

// //////////////
// Constructor //
// //////////////

// @notice Constructor of the smart-contract
// @param registry_address Address of the AuthorizedRegistry contract
// @param version Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address: felt, version: felt
) {
    CommonLib.initialize(registry_address, version);
    return ();
}

// ///////
// View //
// ///////

// @notice Function to get ERC-20 L2 address corresponding to ERC-20 L1 address
// @param l1_address - L1 address of ERC-20 token
// @return address - address of native L2 ERC-20 token
@view
func get_native_token_address{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    l1_address: felt
) -> (address: felt) {
    let (address) = native_token_l2_address.read(l1_address);
    return (address,);
}

// @notice Function to get list of all whitelisted token addresses for a specific L1 ERC-20 token address
// @param l1_address - L1 address of ERC-20 token
// @return addresses_list_len - length of the addresses list
// @return addresses_list - addresses list of L2 whitelisted ERC-20 token contracts
@view
func get_whitelisted_token_addresses{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(l1_address: felt) -> (addresses_list_len: felt, addresses_list: felt*) {
    let (len) = whitelisted_token_l2_address_length.read(l1_address);
    let (addresses_list: felt*) = alloc();
    return _populate_addresses_list(0, len, addresses_list, l1_address);
}

// ///////////
// External //
// ///////////

// @notice Function to initialize ERC-20 token from L1 Starkway contract
// @param token_l1_address - L1 ERC-20 token contract address
// @param token_l2_address - L2 ERC-20 token contract address
@external
func initialize_token{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    token_l1_address: felt, token_l2_address: felt
) {
    let (current_registry_address) = CommonLib.get_registry_address();
    let (current_version) = CommonLib.get_contract_version();

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION);

    let (native_l2_address) = native_token_l2_address.read(token_l1_address);
    // Case when native l2 ERC-20 contract already initialized for this token
    with_attr error_message("Token already initialized") {
        assert native_l2_address = 0;
    }

    native_token_l2_address.write(token_l1_address, token_l2_address);

    return ();
}

// @notice Function to whitelist L2 ERC-20 token addresses
// @param token_l1_address - L1 ERC-20 token contract address
// @param white_listed_l2_address - whitelisted L2 ERC-20 token contract address
@external
func whitelist_token_address{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    token_l1_address: felt, white_listed_l2_address: felt
) {
    let (current_registry_address) = CommonLib.get_registry_address();
    let (current_version) = CommonLib.get_contract_version();

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION);

    let (len) = whitelisted_token_l2_address_length.read(token_l1_address);
    whitelisted_token_l2_address.write(token_l1_address, len, white_listed_l2_address);
    whitelisted_token_l2_address_length.write(token_l1_address, len + 1);

    return ();
}

// @notice Function that gets invoked by L1 Starkway to perform deposit
// @param token_l1_address - L1 ERC-20 token contract address
// @param recipient_address - address to which tokens are to be minted
// @param amount_low - lower bits of Uint256 value of amount
// @param amount_high - higher bits of Uint256 value of amount
@external
func deposit{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    token_l1_address: felt, recipient_address: felt, amount_low: felt, amount_high: felt
) {
    // Make sure that recipient address is not 0 address
    with_attr error_message("Recipient address cannot be 0 address") {
        assert_not_zero(recipient_address);
    }

    // Make sure that the token was initialized
    let (native_token_address) = native_token_l2_address.read(token_l1_address);
    with_attr error_message("Token is not initialized") {
        assert_not_zero(native_token_address);
    }

    // Mint tokens and transfer to user
    let amount_Uint256: Uint256 = Uint256(amount_low, amount_high);
    IERC20.mint(native_token_address, recipient_address, amount_Uint256);

    return ();
}

// ///////////
// Internal //
// ///////////

// @notice Recursive function to populate the addresses list of whitelisted ERC-20 tokens
// @param current_len - current length of list being populated
// @param final_len - final length of the list being populated
// @param addresses_list - list that is getting populated
// @param l1_address - L1 ERC-20 token contract address
// @return addresses_list_len - length of the final list
// @return addresses_list - list of L2 ERC-20 token contract addresses
func _populate_addresses_list{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    current_len: felt, final_len: felt, addresses_list: felt*, l1_address: felt
) -> (addresses_list_len: felt, addresses_list: felt*) {
    alloc_locals;
    if (current_len == final_len) {
        return (final_len, addresses_list);
    }
    let (address) = whitelisted_token_l2_address.read(l1_address, current_len);
    assert addresses_list[current_len] = address;
    return _populate_addresses_list(current_len + 1, final_len, addresses_list, l1_address);
}
