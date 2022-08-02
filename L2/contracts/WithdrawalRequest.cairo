%lang starknet

from contracts.Constants import AccountRegistry_INDEX, L1_ZKX_Address_INDEX, MasterAdmin_ACTION
from contracts.DataTypes import WithdrawalRequest
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAccount import IAccount
from contracts.libraries.Utils import verify_caller_authority
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.math import assert_not_zero

#
# Storage
#

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of Authorized Registry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# Maps request id to withdrawal request
@storage_var
func withdrawal_request_mapping(request_id : felt) -> (res : WithdrawalRequest):
end

#
# Constructor
#

# @notice Constructor of the smart-contract
# @param registry_address_ Address of the AuthorizedRegistry contract
# @param version_ Version of this contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):
    registry_address.write(value=registry_address_)
    contract_version.write(value=version_)
    return ()
end

#
# Getters
#

# @notice Function to get withdrawal request corresponding to the request ID
# @param request_id_ ID of the withdrawal Request
# @return withdrawal_request - returns withdrawal request structure
@view
func get_withdrawal_request_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    request_id_ : felt
) -> (withdrawal_request : WithdrawalRequest):
    let (res : WithdrawalRequest) = withdrawal_request_mapping.read(request_id=request_id_)
    return (withdrawal_request=res)
end

#
# Business logic
#

# @notice function to add withdrawal request to the withdrawal request array
# @param request_id_ ID of the withdrawal Request
# @param user_l1_address_ User's L1 wallet address
# @param ticker_ collateral for the requested withdrawal
# @param amount_ Amount to be withdrawn
@external
func add_withdrawal_request{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    request_id_ : felt, user_l1_address_ : felt, ticker_ : felt, amount_ : felt
):
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (caller) = get_caller_address()

    # fetch account registry contract address
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    )
    # check whether caller is registered user
    let (present) = IAccountRegistry.is_registered_user(
        contract_address=account_registry_address, address_=caller
    )

    with_attr error_message("Called account contract is not registered"):
        assert_not_zero(present)
    end

    # Create a struct with the withdrawal Request
    let new_request = WithdrawalRequest(
        user_l1_address=user_l1_address_, user_l2_address=caller, ticker=ticker_, amount=amount_
    )

    withdrawal_request_mapping.write(request_id=request_id_, value=new_request)
    return ()
end

# @notice Function to handle status updates on withdrawal requests
# @param from_address - The address from where update withdrawal request function is called from
# @param user_l2_address_ - Uers's L2 account contract address
# @param request_id_ - ID of the withdrawal Request
@l1_handler
func update_withdrawal_request{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    from_address : felt, user_l2_address_ : felt, request_id_ : felt
):
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Get L1 ZKX contract address
    let (l1_zkx_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=L1_ZKX_Address_INDEX, version=version
    )

    # Make sure the message was sent by the intended L1 contract.
    with_attr error_message("from address is not matching"):
        assert from_address = l1_zkx_address
    end

    # Create a struct with the withdrawal Request
    let updated_request = WithdrawalRequest(
        user_l1_address=0, user_l2_address=0, ticker=0, amount=0
    )
    withdrawal_request_mapping.write(request_id=request_id_, value=updated_request)

    # update withdrawal history status field to 1
    IAccount.update_withdrawal_history(contract_address=user_l2_address_, request_id_=request_id_)
    return ()
end
