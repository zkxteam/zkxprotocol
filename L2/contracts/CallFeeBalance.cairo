%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_equal
from starkware.starknet.common.syscalls import get_caller_address

# @notice Stores the address of FeeBalance contract
@storage_var
func fee_address() -> (contract_address : felt):
end

# @notice Constructor of the smart-contract
# @param _authAddress Address of the FeeBalance contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    _authAddress : felt
):
    fee_address.write(value=_authAddress)
    return ()
end

# @notice Function to call update_fee_mapping of FeeBalance contract
# @param _address - address of the user whose fee is to be updated
# @param _fee_to_add - fee that is to be added
@external
func update{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    _address : felt, _assetID : felt, _fee_to_add : felt
):
    alloc_locals
    let (fee_addr) = fee_address.read()
    IFeeBalance.update_fee_mapping(
        contract_address=fee_addr, address=_address, assetID_=_assetID, fee_to_add=_fee_to_add
    )
    return ()
end

# @notice FeeBalance interface
@contract_interface
namespace IFeeBalance:
    func update_fee_mapping(address : felt, assetID_ : felt, fee_to_add : felt):
    end
end