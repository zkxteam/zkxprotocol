%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin

/////////////
// Storage //
/////////////

@storage_var
func string_len_mapping(type: felt, id: felt) -> (res: felt) {
}

@storage_var
func string_chars_mapping(type: felt, id: felt, index: felt) -> (res: felt) {
}

namespace StringLib {
    ///////////////////////
    // Library functions //
    ///////////////////////

    func read_string {syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr} (
        type: felt, id: felt
    ) -> (string_len: felt, string: felt*) {
        let (string_len) = string_len_mapping.read(type, id);
        let (string: felt*) = alloc();
        return _recurse_populate_string(
            type=type,
            id=id,
            iterator=0,
            string_len=string_len,
            string=string
        );
    }

    func save_string {syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr} (
        type: felt, id: felt, string_len: felt, string: felt*
    ) {
        string_len_mapping.write(
            type=type, 
            id=id, 
            value=string_len
        );
        return _recurse_save_string(
            type=type,
            id=id,
            iterator=0,
            string_len=string_len,
            string=string
        );
    }

    func remove_existing_string {syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr} (
        type: felt, id: felt
    ) {
        let (string_len) = string_len_mapping.read(type, id);
        if (string_len == 0) {
            return ();
        }
        string_len_mapping.write(
            type=type, 
            id=id, 
            value=0
        );
        return _recurse_remove_string(
            type=type,
            id=id,
            iterator=0,
            string_len=string_len
        );
    }
}

//////////////////////
// Helper functions //
//////////////////////

func _recurse_populate_string {syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr} (
    type: felt, id: felt, iterator: felt, string_len: felt, string: felt*
) -> (string_len: felt, string: felt*) {
    if (iterator == string_len) {
        return (string_len, string);
    }
    let (char) = string_chars_mapping.read(
        type=type, 
        id=id, 
        index=iterator
    );
    assert string[iterator] = char;
    return _recurse_populate_string(
        type,
        id,
        iterator + 1, 
        string_len,
        string
    );
}

func _recurse_save_string {syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr} (
    type: felt, id: felt, iterator: felt, string_len: felt, string: felt*
) {
    if (iterator == string_len) {
        return ();
    }
    // let (char) = string_chars_[iterator_];
    string_chars_mapping.write(
        type=type, 
        id=id, 
        index=iterator, 
        value=string[iterator]
    );
    return _recurse_save_string(
        type,
        id,
        iterator + 1,
        string_len,
        string
    );
}

func _recurse_remove_string {syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr} (
    type: felt, id: felt, iterator: felt, string_len: felt
) {
    if (iterator == string_len) {
        return ();
    }
    string_chars_mapping.write(
        type=type,
        id=id,
        index=iterator,
        value=0
    );
    return _recurse_remove_string(
        type,
        id,
        iterator + 1,
        string_len
    );
}
