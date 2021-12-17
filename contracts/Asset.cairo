%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address


@storage_var
func auth_address() -> (contract_address : felt):
end


struct Asset:
    member ticker: felt
    member short_name: felt
    member tradable: felt
end


@storage_var
func asset(id: felt) -> (res : Asset):
end

@constructor
func constructor{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*, 
    range_check_ptr
}(_authAddress : felt):

    auth_address.write(value = _authAddress)
    return ()
end


@external
func addAsset{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}(id: felt, newAsset: Asset) :
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 1)
    assert_not_zero(access)

    asset.write(id = id, value = newAsset)
    return ()
end


@external
func removeAsset{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}(id: felt) :
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 1)
    assert_not_zero(access)

    asset.write(id = id, value = Asset(ticker = 0, short_name = 0, tradable = 0))
    return ()
end


@external
func modifyAsset{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}(id: felt, editedAsset: Asset) :
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(contract_address = auth_addr, address = caller, action = 1)
    assert_not_zero(access)

    asset.write(id = id, value = editedAsset)
    return ()
end


@view
func getAsset{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}(id: felt) -> (currAsset: Asset) :

    let (currAsset) = asset.read(id = id)
    return (currAsset)
end



@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end