%lang starknet
%builtins pedersen range_check ecdsa

from starkware.starknet.common.syscalls import call_contract, get_caller_address, get_tx_info
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.alloc import alloc
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.Constants import AdminAuth_INDEX, MasterAdmin_ACTION

from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry

// to be set initially in the constructor
@storage_var
func current_version() -> (res: felt) {
}

// @notice Stores the address of Authorized Registry contract
// to be set in the constructor
@storage_var
func registry_address() -> (contract_address: felt) {
}

// @dev - presently we are just going to go with function names or custom index if length > 31
@storage_var
func call_counter(caller: felt, func_name: felt) -> (counter: felt) {
}

// @dev - this stores whether caller has been paid for hash -> 1 => hash recorded but not paid, 2 => paid
@storage_var
func caller_hash_status(caller: felt, transaction_hash: felt) -> (res: felt) {
}

// @notice - to be set in the constructor
// @dev - this will help us get the underlying contracts address through the registry
@storage_var
func self_index() -> (index: felt) {
}

// stores caller hash count
@storage_var
func hash_count(caller: felt) -> (res: felt) {
}

// stores list of hashes for a caller
@storage_var
func hash_list_for_caller(caller: felt, index: felt) -> (res: felt) {
}

// index + version = address
// this function is called by constructor of relay to setup registry address, index and version
func initialize{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt, index_: felt
) {
    registry_address.write(registry_address_);
    current_version.write(version_);
    self_index.write(index_);
    return ();
}

// @notice - helper function to verify authority of caller for action
// gets admin address from authorized registry
// asks admin whether caller is authorized for action
func verify_caller_authority{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    action: felt
) -> () {
    let (registry) = registry_address.read();
    let (version) = current_version.read();

    let (caller) = get_caller_address();
    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    );
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=action
    );

    assert access = 1;
    return ();
}

// @notice - increments call counter for given function_name for current caller
func increment_call_counter{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    function_name: felt
) -> () {
    let (caller) = get_caller_address();
    let (current_count) = call_counter.read(caller, function_name);
    call_counter.write(caller, function_name, current_count + 1);
    return ();
}

// stores hash in caller hash array after incrementing caller hash count
func store_caller_hash{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() {
    let (caller) = get_caller_address();
    let (tx_info) = get_tx_info();
    let (current_count) = hash_count.read(caller);
    if (current_count == 0) {
        hash_count.write(caller, current_count + 1);
        hash_list_for_caller.write(caller, 0, tx_info.transaction_hash);
        return ();
    }
    hash_count.write(caller, current_count + 1);
    hash_list_for_caller.write(caller, current_count, tx_info.transaction_hash);
    return ();
}

// recursively creates list of transaction hashes for a caller

func create_list{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    caller: felt, total_length: felt, current_index: felt, hash_list: felt*
) {
    if (current_index == total_length) {
        return ();
    }
    let (transaction_hash) = hash_list_for_caller.read(caller, current_index);
    assert [hash_list + current_index] = transaction_hash;
    create_list(caller, total_length, current_index + 1, hash_list);
    return ();
}

// @notice - records <caller, transaction_hash> as seen (value 1)
func set_caller_hash_status{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() {
    let (caller) = get_caller_address();
    let (tx_info) = get_tx_info();
    caller_hash_status.write(caller, tx_info.transaction_hash, 1);
    return ();
}

// @notice - helper function to get address of underlying contract
func get_inner_contract{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    address: felt
) {
    let (registry) = registry_address.read();
    let (version) = current_version.read();
    let (index) = self_index.read();

    let (inner_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=index, version=version
    );
    return (inner_address,);
}

// @notice - helper function to do necessary bookkeeping
// @dev - this is the only function called by Relay contract to do bookkeeping
func record_call_details{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    function_name: felt
) {
    store_caller_hash();
    increment_call_counter(function_name);
    set_caller_hash_status();
    return ();
}

@view
func get_current_version{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (res) = current_version.read();
    return (res,);
}

@view
func get_caller_hash_status{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    caller: felt, transaction_hash: felt
) -> (res: felt) {
    let (res) = caller_hash_status.read(caller, transaction_hash);
    return (res,);
}

@view
func get_call_counter{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    caller: felt, function_name: felt
) -> (count: felt) {
    let (count) = call_counter.read(caller, function_name);
    return (count,);
}

@view
func get_registry_address_at_relay{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    ) -> (address: felt) {
    let (address) = registry_address.read();
    return (address,);
}

@view
func get_self_index{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    index: felt
) {
    let (index) = self_index.read();
    return (index,);
}

// @notice - gets list of transaction hashes for a caller (length of this list = no. of calls done by this caller)
@view
func get_caller_hash_list{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    caller: felt
) -> (hash_list_len: felt, hash_list: felt*) {
    alloc_locals;
    let (local count) = hash_count.read(caller);
    if (count == 0) {
        return (0, cast(0, felt*));
    }
    let (hash_list: felt*) = alloc();
    create_list(caller, count, 0, hash_list);
    return (count, hash_list);
}

// @dev - All the following functions require master admin access currently - action 0

@external
func set_current_version{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    val: felt
) -> () {
    verify_caller_authority(MasterAdmin_ACTION);  // only master admin action allowed i.e. action 0
    current_version.write(val);
    return ();
}

// @notice - can be called by some reward paying authority to mark a transaction_hash for a caller as paid (value 2)
@external
func mark_caller_hash_paid{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    caller: felt, transaction_hash: felt
) {
    verify_caller_authority(MasterAdmin_ACTION);
    let (is_seen) = caller_hash_status.read(caller, transaction_hash);
    assert is_seen = 1;
    caller_hash_status.write(caller, transaction_hash, 2);
    return ();
}

// @notice - can be called by some reward paying authority to reset the call counters after remunerating nodes
// @dev - requires master admin access (action - 0)
@external
func reset_call_counter{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    caller: felt, function_name: felt
) {
    verify_caller_authority(MasterAdmin_ACTION);
    call_counter.write(caller, function_name, 0);
    return ();
}

// @notice - call be called by admin to change index of underlying contract
@external
func set_self_index{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(index: felt) {
    verify_caller_authority(MasterAdmin_ACTION);
    self_index.write(index);
    return ();
}
