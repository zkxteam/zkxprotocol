%lang starknet
%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero, assert_nn, assert_le
from starkware.cairo.common.alloc import alloc

// //////////
// Structs //
// //////////

struct Position {
    asset_id: felt,
    coll_id: felt,
}

// //////////
// Storage //
// //////////

@storage_var
func position_mapping(position_id: felt) -> (position: Position) {
}

@storage_var
func no_of_pos() -> (length: felt) {
}

@storage_var
func position_array(index: felt) -> (position_id: felt) {
}

@storage_var
func arr_len() -> (len: felt) {
}

// ///////
// View //
// ///////

@view
func return_array{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    array_list_len: felt, array_list: Position*
) {
    alloc_locals;

    let (array_list: Position*) = alloc();
    return populate_array(array_list_len=0, array_list=array_list);
}

@view
func get_position{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(id_: felt) -> (
    res: Position
) {
    let (pos) = position_mapping.read(position_id=id_);
    return (pos,);
}

@view
func get_position_array{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id_: felt
) -> (res: Position) {
    let (pos) = position_array.read(index=id_);
    let (pos_deets) = position_mapping.read(position_id=pos);
    return (pos_deets,);
}

// ///////////
// External //
// ///////////

@external
func add_position{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id_: felt, position_new_: Position
) -> (res: felt) {
    position_mapping.write(position_id=id_, value=position_new_);
    add_to_array(id_=id_);
    return (1,);
}

@external
func remove_from_array{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    id_: felt
) -> (res: felt) {
    alloc_locals;
    let (pos_id) = position_array.read(index=id_);
    if (pos_id == 0) {
        return (0,);
    }

    let (arr_len) = no_of_pos.read();
    let (last_id) = position_array.read(index=arr_len - 1);

    position_array.write(index=id_, value=last_id);
    position_array.write(index=arr_len - 1, value=0);

    no_of_pos.write(arr_len - 1);
    return (1,);
}

// ///////////
// Internal //
// ///////////

func add_to_array{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(id_: felt) -> (
    res: felt
) {
    let (arr_len) = no_of_pos.read();
    position_array.write(index=arr_len, value=id_);
    no_of_pos.write(arr_len + 1);
    return (1,);
}

func populate_array{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    array_list_len: felt, array_list: Position*
) -> (array_list_len: felt, array_list: Position*) {
    let (pos) = position_array.read(index=array_list_len);

    if (pos == 0) {
        return (array_list_len, array_list);
    }

    let (pos_deets) = position_mapping.read(position_id=pos);

    if (pos_deets.coll_id == 0) {
        return (array_list_len, array_list);
    }

    assert array_list[array_list_len] = pos_deets;
    return populate_array(array_list_len + 1, array_list);
}
