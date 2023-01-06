%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_nn, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import get_caller_address

from contracts.Constants import AccountDeployer_INDEX, MasterAdmin_ACTION, Trading_INDEX
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority

//##########
// Storage #
//##########

// Stores all account contract addresses of users
@storage_var
func account_registry(index: felt) -> (address: felt) {
}

// Stores length of the account registry
@storage_var
func account_registry_len() -> (len: felt) {
}

// Stores account contract address to boolean mapping to check whether a user is present
@storage_var
func account_present(address: felt) -> (present: felt) {
}

//##############
// Constructor #
//##############

// @notice Constructor for the smart-contract
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

// @notice Function to check whether a user is present in account registry
// @param address_ Address of the user that is to be checked
// @returns present - 0 if not present, 1 if present
@view
func is_registered_user{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address_: felt
) -> (present: felt) {
    let (present) = account_present.read(address=address_);
    return (present,);
}

// @notice Function to get the length of the account registry
// @returns len - length of the registry array
@view
func get_registry_len{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    len: felt
) {
    let (reg_len) = account_registry_len.read();
    return (reg_len,);
}

// @notice Helper function to get a user batch
// @param starting_index_ - Index at which begin populating the array
// @param ending_index_ - Upper limit of the batch
@view
func get_batch{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    starting_index_: felt, ending_index_: felt
) -> (account_registry_len: felt, account_registry: felt*) {
    alloc_locals;

    local ending_index;
    let (reg_len) = account_registry_len.read();
    let is_longer = is_le(reg_len, ending_index_);

    // Check if batch must be truncated
    if (is_longer == 1) {
        ending_index = reg_len;
    } else {
        ending_index = ending_index_;
    }

    let (account_registry_list: felt*) = alloc();
    return populate_account_registry(
        iterator_=0,
        starting_index_=starting_index_,
        ending_index_=ending_index,
        account_registry_list_=account_registry_list,
    );
}

// @notice Function to get all user account addresses
// @param starting_index_ - Index from which to fetch the array
// @param num_accounts - Number of accounts to fetch from the array
// @returns account_registry_len - Length of the account registry
// @returns account_registry - registry of account addresses
@view
func get_account_registry{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    starting_index_: felt, num_accounts_: felt
) -> (account_registry_len: felt, account_registry: felt*) {
    with_attr error_message("AccountRegistry: Starting index cannot be negative") {
        assert_nn(starting_index_);
    }

    with_attr error_message("AccountRegistry: Number of accounts cannot be negative or zero") {
        assert_lt(0, num_accounts_);
    }

    let ending_index = starting_index_ + num_accounts_;
    let (reg_len) = account_registry_len.read();
    with_attr error_message("AccountRegistry: Cannot retrieve the specified num of accounts") {
        assert_le(ending_index, reg_len);
    }

    let (account_registry_list: felt*) = alloc();
    return populate_account_registry(0, starting_index_, ending_index, account_registry_list);
}

//#####################
// External Functions #
//#####################

// @notice add to account registry
// @param address_ - L2 account contract address of the user
@external
func add_to_account_registry{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    address_: felt
) {
    // Check whether the call is from account deployer contract
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (account_deployer_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountDeployer_INDEX, version=version
    );
    with_attr error_message("AccountRegistry: Unauthorized caller for add_to_account_registry") {
        assert caller = account_deployer_address;
    }

    with_attr error_message("AccountRegistry: Address cannot be 0") {
        assert_not_zero(address_);
    }

    let (is_present) = account_present.read(address=address_);
    if (is_present == FALSE) {
        let (reg_len) = account_registry_len.read();
        account_registry.write(index=reg_len, value=address_);
        account_registry_len.write(reg_len + 1);
        account_present.write(address=address_, value=1);
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }
    return ();
}

// @notice External function called to remove account address from registry
// @param id_ - Index of the element in the list
@external
func remove_from_account_registry{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id_: felt
) -> () {
    with_attr error_message(
            "AccountRegistry: Unathorized caller for remove_from_account_registry") {
        let (registry) = CommonLib.get_registry_address();
        let (version) = CommonLib.get_contract_version();
        verify_caller_authority(registry, version, MasterAdmin_ACTION);
    }

    with_attr error_message("AccountRegistry: 0 passed as ID for removal") {
        assert_nn(id_);
    }

    let (reg_len) = account_registry_len.read();
    with_attr error_message("AccountRegistry: id greater than account registry len") {
        assert_lt(id_, reg_len);
    }

    with_attr error_message("AccountRegistry: Registry is empty") {
        assert_not_zero(reg_len);
    }

    let (account_address) = account_registry.read(index=id_);
    with_attr error_message("AccountRegistry: Account address doesn't exist at the index") {
        assert_not_zero(account_address);
    }

    let (last_account_address) = account_registry.read(index=reg_len - 1);

    account_registry.write(index=id_, value=last_account_address);
    account_registry.write(index=reg_len - 1, value=0);

    account_registry_len.write(reg_len - 1);
    account_present.write(address=account_address, value=FALSE);

    return ();
}

//#####################
// Internal Functions #
//#####################

// @notice Internal Function called by get_account_registry to recursively add accounts to the registry and return it
// @param iterator_ - The index of pointer of the array to be returned
// @param starting_index_ - The current index of the registry array
// @param ending_index_ - The index at which to stop
// @param account_registry_list_ - Registry of accounts filled up to the index
// @returns account_registry_len - Length of the account registry
// @returns account_registry - registry of account addresses
func populate_account_registry{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    iterator_: felt, starting_index_: felt, ending_index_: felt, account_registry_list_: felt*
) -> (account_registry_len: felt, account_registry: felt*) {
    if (starting_index_ == ending_index_) {
        return (iterator_, account_registry_list_);
    }
    let (address) = account_registry.read(index=starting_index_);

    assert account_registry_list_[iterator_] = address;
    return populate_account_registry(
        iterator_ + 1, starting_index_ + 1, ending_index_, account_registry_list_
    );
}
