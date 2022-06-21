%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address, get_block_timestamp

# status 0: initialized
# status 1: consumed
struct WithdrawalRequest:
    member l2_account_address : felt
    member collateral_id : felt
    member amount : felt
    member timestamp : felt
    member status : felt
end

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


# @notice Internal Function called by get_withdrawal_request_data to recursively add requests to the array and return it
# @param withdrawal_request_list_len_ - Stores the current length of the populated withdrawal request list
# @param withdrawal_request_list_ - list of requests filled up to the index
# @returns withdrawal_request_list_len_ - Length of withdrawal request list length
# @returns withdrawal_request_list_ - withdrawal request list
func populate_withdrawals_request_array{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    withdrawal_request_list_len_ : felt, 
    withdrawal_request_list_ : WithdrawalRequest*
) -> (withdrawal_request_list_len_ : felt, withdrawal_request_list_ : WithdrawalRequest*):
    alloc_locals
    let (request : WithdrawalRequest) = withdrawal_request_array.read(index=withdrawal_request_list_len_)

    if request.l2_account_address == 0:
        return (withdrawal_request_list_len_, withdrawal_request_list_)
    end

    assert withdrawal_request_list_[withdrawal_request_list_len_] = request
    return populate_withdrawals_request_array(withdrawal_request_list_len_ + 1, withdrawal_request_list_)
end

# @notice Function to get all withdrawal requests
# @return withdrawal_request_list_len - Length of the withdrawal request array
# @return withdrawal_request_list - withdrawal request array
@view
func get_withdrawal_request_data{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    withdrawal_request_list_len : felt, 
    withdrawal_request_list : WithdrawalRequest*
):
    alloc_locals
    let (withdrawal_request_list : WithdrawalRequest*) = alloc()
    let (withdrawal_request_list_len_, withdrawal_request_list_) = populate_withdrawals_request_array(
        0, withdrawal_request_list
    )
    return (withdrawal_request_list_len=withdrawal_request_list_len_, withdrawal_request_list=withdrawal_request_list_)
end

# @notice function to add withdrawal request to the withdrawal request array
# @param l2_account_address_ Address of L2 account contract
# @param collateral_id_ Id of the collateral for the requested withdrawal
# @param amount_ Amount to be withdrawn
# @param status_ status of the withdrawal
@external
func add_withdrawal_request{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    l2_account_address_ : felt, 
    collateral_id_ : felt, 
    amount_ : felt
):
    # Add authorization
    let (caller) = get_caller_address()

    let (arr_len) = withdrawal_request_array_len.read()

    let (timestamp_) = get_block_timestamp()
    # Create a struct with the withdrawal Request
    let new_request = WithdrawalRequest(
        l2_account_address = l2_account_address_,
        collateral_id = collateral_id_,
        amount=amount_,
        timestamp = timestamp_,
        status=0,
    )

    withdrawal_request_array.write(index=arr_len, value=new_request)
    withdrawal_request_array_len.write(arr_len + 1)
    return ()
end

# @notice Internal function to recursively find the index of the withdrawal request to be updated
# @param l2_account_address_ - User's Account contract address
# @param collateral_id_ - Id of the collateral on which user submitted withdrawal request
# @param amount_ - Amount of funds that user has withdrawn
# @param timestamp_ - Time at which user submitted withdrawal request
# @param status_ - Status of the withdrawal request
# @param arr_len_ - current index which is being checked to be updated
func find_index_to_be_updated_recurse{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    l2_account_address_ : felt, 
    collateral_id_ : felt, 
    amount_ : felt, 
    timestamp_ : felt,
    status_ : felt, 
    arr_len_ : felt
) -> (index : felt):
    if arr_len_ == 0:
        return (-1)
    end
    let (request : WithdrawalRequest) = withdrawal_request_array.read(index=arr_len_ - 1)
    if request.l2_account_address == l2_account_address_:
        if request.collateral_id == collateral_id_:
            if request.amount == amount_:
                if request.timestamp == timestamp_:
                    if request.status == 0:
                        return (arr_len_ - 1)
                    else:
                        tempvar syscall_ptr = syscall_ptr
                        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                        tempvar range_check_ptr = range_check_ptr
                    end
                else:
                    tempvar syscall_ptr = syscall_ptr
                    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                    tempvar range_check_ptr = range_check_ptr
                end
            else:
                tempvar syscall_ptr = syscall_ptr
                tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                tempvar range_check_ptr = range_check_ptr
            end
        else:
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        end
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end
    tempvar syscall_ptr = syscall_ptr
    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
    tempvar range_check_ptr = range_check_ptr
    return find_index_to_be_updated_recurse(l2_account_address_, collateral_id_, amount_, timestamp_, status_, arr_len_ - 1)
end


# @notice Function to handle status updates on withdrawal requests
# @param from_address - The address from where update withdrawal request function is called from
# @param l2_account_address_ - User's Account contract address
# @param collateral_id_ - Id of the collateral on which user submitted withdrawal request
# @param amount_ - Amount of funds that user has withdrawn
# @param timestamp_ - Time at which user submitted withdrawal request
# @param status_ - Status of the withdrawal request
@l1_handler
func update_withdrawal_request{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    from_address : felt,
    l2_account_address_ : felt, 
    collateral_id_ : felt, 
    amount_ : felt, 
    timestamp_ : felt,
    status_ : felt
):

    # Make sure the message was sent by the intended L1 contract.
    # assert from_address = L1_CONTRACT_ADDRESS

    let (arr_len) = withdrawal_request_array_len.read()
    let (index) = find_index_to_be_updated_recurse(l2_account_address_, collateral_id_, amount_, timestamp_, status_, arr_len)
    if index != -1:
        # Create a struct with the withdrawal Request
        let updated_request = WithdrawalRequest(
            l2_account_address = l2_account_address_,
            collateral_id = collateral_id_,
            amount=amount_,
            timestamp = timestamp_,
            status=1,
        )
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
        withdrawal_request_array.write(index=index, value=updated_request)
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end
    return ()
end