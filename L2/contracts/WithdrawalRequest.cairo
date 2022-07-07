%lang starknet

%builtins pedersen range_check ecdsa

from contracts.Constants import AccountRegistry_INDEX, AdminAuth_INDEX, MasterAdmin_ACTION
from contracts.DataTypes import WithdrawalRequest
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.interfaces.IAccount import IAccount
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

# Stores withdrawal requests
@storage_var
func withdrawal_request_array(index : felt) -> (res : WithdrawalRequest):
end

# stores the length of the withdrawal request array
@storage_var
func withdrawal_request_array_len() -> (len : felt):
end

# @notice stores the address of L1 zkx contract
@storage_var
func L1_zkx_address() -> (res : felt):
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
# Setters
#

# @notice set L1 zkx contract address function
# @param address - L1 zkx contract address as an argument
@external
func set_L1_zkx_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    l1_zkx_address : felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    )

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=MasterAdmin_ACTION
    )
    assert_not_zero(access)

    L1_zkx_address.write(value=l1_zkx_address)
    return ()
end

#
# Getters
#

# @notice Internal Function called by get_withdrawal_request_data to recursively add requests to the array and return it
# @param withdrawal_request_list_len_ - Stores the current length of the populated withdrawal request list
# @param withdrawal_request_list_ - list of requests filled up to the index
# @returns withdrawal_request_list_len_ - Length of withdrawal request list length
# @returns withdrawal_request_list_ - withdrawal request list
func populate_withdrawals_request_array{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr
}(withdrawal_request_list_len_ : felt, withdrawal_request_list_ : WithdrawalRequest*) -> (
    withdrawal_request_list_len_ : felt, withdrawal_request_list_ : WithdrawalRequest*
):
    alloc_locals
    let (request : WithdrawalRequest) = withdrawal_request_array.read(
        index=withdrawal_request_list_len_
    )

    if request.user_l1_address == 0:
        return (withdrawal_request_list_len_, withdrawal_request_list_)
    end

    assert withdrawal_request_list_[withdrawal_request_list_len_] = request
    return populate_withdrawals_request_array(
        withdrawal_request_list_len_ + 1, withdrawal_request_list_
    )
end

# @notice Function to get all withdrawal requests
# @return withdrawal_request_list_len - Length of the withdrawal request array
# @return withdrawal_request_list - withdrawal request array
@view
func get_withdrawal_request_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    ) -> (withdrawal_request_list_len : felt, withdrawal_request_list : WithdrawalRequest*):
    alloc_locals
    let (withdrawal_request_list : WithdrawalRequest*) = alloc()
    let (
        withdrawal_request_list_len_, withdrawal_request_list_
    ) = populate_withdrawals_request_array(0, withdrawal_request_list)
    return (
        withdrawal_request_list_len=withdrawal_request_list_len_,
        withdrawal_request_list=withdrawal_request_list_,
    )
end

#
# Business logic
#

# @notice function to add withdrawal request to the withdrawal request array
# @param user_l1_address_ User's L1 wallet address
# @param ticker_ collateral for the requested withdrawal
# @param amount_ Amount to be withdrawn
# @param timestamp_ - Time at which user submitted withdrawal request
# @param L1_fee_amount_ - Gas fee in L1
# @param L1_fee_ticker_ - Collateral used to pay L1 gas fee
@external
func add_withdrawal_request{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    user_l1_address_ : felt,
    ticker_ : felt,
    amount_ : felt,
    timestamp_ : felt,
    L1_fee_amount_ : felt,
    L1_fee_ticker_ : felt,
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

    let (arr_len) = withdrawal_request_array_len.read()
    # Create a struct with the withdrawal Request
    let new_request = WithdrawalRequest(
        user_l1_address=user_l1_address_,
        user_l2_address=caller,
        ticker=ticker_,
        amount=amount_,
        timestamp=timestamp_,
        status=0,
        L1_fee_amount=L1_fee_amount_,
        L1_fee_ticker=L1_fee_ticker_,
    )

    withdrawal_request_array.write(index=arr_len, value=new_request)
    withdrawal_request_array_len.write(arr_len + 1)
    return ()
end

# @notice Internal function to recursively find the index of the withdrawal request to be updated
# @param user_l1_address_ - User's L1 wallet address
# @param ticker_ - collateral on which user submitted withdrawal request
# @param amount_ - Amount of funds that user has withdrawn
# @param timestamp_ - Time at which user submitted withdrawal request
# @param status_ - Status of the withdrawal request
# @param arr_len_ - current index which is being checked to be updated
func find_index_to_be_updated_recurse{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr
}(
    user_l1_address_ : felt,
    ticker_ : felt,
    amount_ : felt,
    timestamp_ : felt,
    status_ : felt,
    arr_len_ : felt,
) -> (index : felt):
    alloc_locals

    if arr_len_ == 0:
        return (-1)
    end

    let (request : WithdrawalRequest) = withdrawal_request_array.read(index=arr_len_ - 1)

    local first_check_counter
    local second_check_counter
    local third_check_counter
    local fourth_check_counter
    local fifth_check_counter
    if request.user_l1_address == user_l1_address_:
        first_check_counter = 1
    end
    if request.ticker == ticker_:
        second_check_counter = 1
    end
    if request.amount == amount_:
        third_check_counter = 1
    end
    if request.timestamp == timestamp_:
        fourth_check_counter = 1
    end
    if request.status == 0:
        fifth_check_counter = 1
    end

    let counter = first_check_counter + second_check_counter + third_check_counter + fourth_check_counter + fifth_check_counter
    if counter == 5:
        return (arr_len_ - 1)
    end
    return find_index_to_be_updated_recurse(
        user_l1_address_, ticker_, amount_, timestamp_, status_, arr_len_ - 1
    )
end

# @notice Function to handle status updates on withdrawal requests
# @param from_address - The address from where update withdrawal request function is called from
# @param user_l1_address_ - User's L1 wallet address
# @param user_l2_address_ - Uers's L2 account contract address
# @param ticker_ - Collateral on which user submitted withdrawal request
# @param collateral_id_ - Id of the collateral on which user submitted withdrawal request
# @param amount_ - Amount of funds that user has withdrawn
# @param timestamp_ - Time at which user submitted withdrawal request
# @param node_operator_L1_address_ - Node operators L1 address
# @param L1_fee_amount_ - Gas fee in L1
# @param L1_fee_ticker_ - ticker used to pay L1 gas fee
# @param L1_fee_collateral_id_ - Collateral ID used to pay L1 gas fee
@l1_handler
func update_withdrawal_request{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    from_address : felt,
    user_l1_address_ : felt,
    user_l2_address_ : felt,
    ticker_ : felt,
    collateral_id_ : felt,
    amount_ : felt,
    timestamp_ : felt,
    node_operator_L1_address_ : felt,
    L1_fee_amount_ : felt,
    L1_fee_ticker_ : felt,
    L1_fee_collateral_id_ : felt,
):
    # Make sure the message was sent by the intended L1 contract.
    let (l1_zkx_address) = L1_zkx_address.read()
    with_attr error_message("from address is not matching"):
        assert from_address = l1_zkx_address
    end

    let (arr_len) = withdrawal_request_array_len.read()
    let (index) = find_index_to_be_updated_recurse(
        user_l1_address_, ticker_, amount_, timestamp_, 0, arr_len
    )
    if index != -1:
        # Create a struct with the withdrawal Request
        let updated_request = WithdrawalRequest(
            user_l1_address=user_l1_address_,
            user_l2_address=user_l2_address_,
            ticker=ticker_,
            amount=amount_,
            timestamp=timestamp_,
            status=1,
            L1_fee_amount=L1_fee_amount_,
            L1_fee_ticker=L1_fee_ticker_,
        )
        withdrawal_request_array.write(index=index, value=updated_request)

        # update L1 fee and node operators L1 wallet address in withdrawal history
        IAccount.update_withdrawal_history(
            contract_address=user_l2_address_,
            collateral_id_=collateral_id_,
            amount_=amount_,
            timestamp_=timestamp_,
            node_operator_L1_address_=node_operator_L1_address_,
            L1_fee_amount_=L1_fee_amount_,
            L1_fee_collateral_id_=L1_fee_collateral_id_,
        )
        return ()
    end
    return ()
end
