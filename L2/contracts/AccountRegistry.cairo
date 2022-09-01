%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_le, assert_lt, assert_nn, assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address

from contracts.Constants import AccountDeployer_INDEX, MasterAdmin_ACTION, Trading_INDEX
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.Utils import verify_caller_authority

###########
# Storage #
###########

# Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# Stores the address of AuthorizedRegistry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# Stores all account contract addresses of users
@storage_var
func account_registry(index : felt) -> (address : felt):
end

# Stores length of the account registry
@storage_var
func account_registry_len() -> (len : felt):
end

# Stores account contract address to boolean mapping to check whether a user is present
@storage_var
func account_present(address : felt) -> (present : felt):
end

###############
# Constructor #
###############

# @notice Constructor for the smart-contract
# @param registry_address_ Address of the AuthorizedRegistry contract
# @param version_ Version of this contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, version_ : felt
):
    with_attr error_message("Registry address and version cannot be 0"):
        assert_not_zero(registry_address_)
        assert_not_zero(version_)
    end

    registry_address.write(value=registry_address_)
    contract_version.write(value=version_)
    return ()
end

##################
# View Functions #
##################

# @notice Function to check whether a user is present in account registry
# @param address_ Address of the user that is to be checked
# @returns present - 0 if not present, 1 if present
@view
func is_registered_user{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address_ : felt
) -> (present : felt):
    let (present) = account_present.read(address=address_)
    return (present)
end

# @notice Function to get the length of the account registry
# @returns len - length of the registry array
@view
func get_registry_len{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    len : felt
):
    let (reg_len) = account_registry_len.read()
    return (reg_len)
end

# @notice Function to get all user account addresses
# @param starting_index_ - Index from which to fetch the array
# @param num_accounts - Number of accounts to fetch from the array
# @returns account_registry_len - Length of the account registry
# @returns account_registry - registry of account addresses
@view
func get_account_registry{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    starting_index_ : felt, num_accounts_ : felt
) -> (account_registry_len : felt, account_registry : felt*):
    with_attr error_message("Starting index cannot be negative"):
        assert_nn(starting_index_)
    end

    with_attr error_message("Number of accounts cannot be negative or zero"):
        assert_lt(0, num_accounts_)
    end

    let ending_index = starting_index_ + num_accounts_
    let (reg_len) = account_registry_len.read()
    with_attr error_message("Cannot retrieve the specified num of accounts"):
        assert_le(ending_index, reg_len)
    end

    let (account_registry_list : felt*) = alloc()
    return populate_account_registry(0, starting_index_, ending_index, account_registry_list)
end

######################
# External Functions #
######################

# @notice add to account registry
# @param address_ - L2 account contract address of the user
# @return 1 - If successfully added
@external
func add_to_account_registry{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    address_ : felt
) -> (res : felt):
    # Check whether the call is from account deployer contract
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (account_deployer_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountDeployer_INDEX, version=version
    )
    with_attr error_message("Caller is not authorized to add account to registry"):
        assert caller = account_deployer_address
    end

    with_attr error_message("Address cannot be zero"):
        assert_not_zero(address_)
    end

    let (is_present) = account_present.read(address=address_)
    if is_present == FALSE:
        let (reg_len) = account_registry_len.read()
        account_registry.write(index=reg_len, value=address_)
        account_registry_len.write(reg_len + 1)
        account_present.write(address=address_, value=1)
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end
    return (1)
end

# @notice External function called to remove account address from registry
# @param id_ - Index of the element in the list
@external
func remove_from_account_registry{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr
}(id_ : felt) -> ():
    with_attr error_message("Caller is not Master Admin"):
        let (registry) = registry_address.read()
        let (version) = contract_version.read()
        verify_caller_authority(registry, version, MasterAdmin_ACTION)
    end

    with_attr error_message("id_ cannot be negative"):
        assert_nn(id_)
    end

    let (reg_len) = account_registry_len.read()
    with_attr error_message(
            "id_ cannot be greater than or equal to the length of the registry array"):
        assert_lt(id_, reg_len)
    end

    with_attr error_message("The registry array is empty"):
        assert_not_zero(reg_len)
    end

    let (account_address) = account_registry.read(index=id_)
    with_attr error_message("Account address does not exists in that index"):
        assert_not_zero(account_address)
    end

    let (last_account_address) = account_registry.read(index=reg_len - 1)

    account_registry.write(index=id_, value=last_account_address)
    account_registry.write(index=reg_len - 1, value=0)

    account_registry_len.write(reg_len - 1)
    account_present.write(address=account_address, value=FALSE)

    return ()
end

######################
# Internal Functions #
######################

# @notice Internal Function called by get_account_registry to recursively add accounts to the registry and return it
# @param iterator_ - The index of pointer of the array to be returned
# @param starting_index_ - The current index of the registry array
# @param ending_index_ - The index at which to stop
# @param account_registry_list_ - Registry of accounts filled up to the index
# @returns account_registry_len - Length of the account registry
# @returns account_registry - registry of account addresses
func populate_account_registry{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    iterator_, starting_index_ : felt, ending_index_ : felt, account_registry_list_ : felt*
) -> (account_registry_len : felt, account_registry : felt*):
    if starting_index_ == ending_index_:
        return (iterator_, account_registry_list_)
    end
    let (address) = account_registry.read(index=starting_index_)

    assert account_registry_list_[iterator_] = address
    return populate_account_registry(
        iterator_ + 1, starting_index_ + 1, ending_index_, account_registry_list_
    )
end
