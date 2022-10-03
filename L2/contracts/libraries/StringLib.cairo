%lang starknet
%builtins pedersen range_check

from starkware.cairo.common.cairo_builtins import HashBuiltin

/////////////
// Storage //
/////////////

@storage_var
func string_len(type: felt, id: felt) -> (res: felt) {
}

@storage_var
func string_chars(type: felt, id: felt, index: felt) -> (res: felt) {
}

namespace StringLib {
    ///////////////////////
    // Library functions //
    ///////////////////////

    func read_string{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
        type_: felt, id_: felt
    ) -> (string_len: felt, string_chars: felt*) {
        let (string_len) = string_len.read(type_, id_);
        let (string_chars: felt*) = alloc();
        recurse_populate_string(
            type_=type_,
            id_=id_,
            current_len_=0,
            final_len_=string_len,
            chars_=string_chars
        );
        return (link_len, link_chars,);
    }

    func save_string{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
        type_: felt, id_: felt, string_len_: felt, string_chars_: felt*
    ) {
        string_len.write(type_, id_, string_len_);
        return recurse_save_chars(
            type_,
            id_,
            iterator_=0,
            string_len,
            string_chars_
        );
    }

    func remove_existing_string{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
        type_: felt, id_: felt
    ) {
        let (string_len) = string_len.read(type_, id_);
        if (link_len == 0) {
            return ();
        }
        string_len.write(
            type=type_, 
            id=id_, 
            value=0
        );
        return recurse_remove_chars(
            type_, 
            id_, 
            iterator_=0, 
            final_length_=string_len
        );
    }
}

//////////////////////
// Helper functions //
//////////////////////

func _recurse_populate_string{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    type_: felt, id_: felt, iterator_: felt, final_len_: felt, chars_: felt*
) -> () {
    if (iterator_ == final_len_) {
        return ();
    }
    let (char) = string_chars.read(type_, id_, iterator_);
    assert chars_[iterator_] = char;
    return recurse_populate_string(
        type_,
        id_,
        iterator_ + 1, 
        final_len_, 
        chars_
    );
}

func _recurse_save_chars{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    type_: felt, id_: felt, iterator_: felt, string_len_: felt, string_chars_: felt*
) {
    if (iterator_ == string_len_) {
        return ();
    }
    // let (char) = string_chars_[iterator_];
    string_chars.write(
        type=type_, 
        id=id_, 
        index=iterator_, 
        value=string_chars_[iterator_]
    );
    return recurse_save_chars(
        type_,
        id_,
        iterator_ + 1,
        string_len_,
        string_chars_
    );
}

func _recurse_remove_chars{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    type_: felt, id_: felt, iterator_: felt, final_length_: felt
) {
    if (iterator_ == final_length_) {
        return ();
    }
    string_chars.write(
        type=type_,
        id=id_,
        index=iterator_,
        value=0
    );
    return recurse_remove_chars(
        type_,
        id_,
        iterator_+1,
        final_length_
    );
}
