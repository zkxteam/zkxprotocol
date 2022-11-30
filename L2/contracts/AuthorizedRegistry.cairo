%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from contracts.Constants import AdminAuth_INDEX, ManageAuthRegistry_ACTION
from contracts.interfaces.IAdminAuth import IAdminAuth

from starkware.starknet.common.syscalls import get_caller_address

//#########
// Events #
//#########

// Event emitted whenever a new address is added to the registry
@event
func updated_registry(index: felt, version: felt, address: felt) {
}

//##########
// Storage #
//##########

// @notice Stores the address for a specific zkx contract corresponding to the version
// Index - Contract information
// 0 - AdminAuth
// 1 - Asset
// 2 - Market
// 3 - FeeDiscount
// 4 - TradingFees
// 5 - Trading
// 6 - FeeBalance
// 7 - Holding
// 8 - EmergencyFund
// 9 - LiquidityFund
// 10 - InsuranceFund
// 11 - Liquidate
// 12 - RiskManagement
@storage_var
func contract_registry(index: felt, version: felt) -> (address: felt) {
}

//##############
// Constructor #
//##############

// @notice Constructor for the smart-contract
// @param auth_address_ - Address of the AdminAuth Contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    auth_address_: felt
) {
    with_attr error_message("AuthRegistry: AdminAuth contract address cannot be 0") {
        assert_not_zero(auth_address_);
    }
    contract_registry.write(index=AdminAuth_INDEX, version=1, value=auth_address_);
    return ();
}

//#################
// View Functions #
//#################

// @notice Function to find whether an address has permission to perform certain action
// @param address - Address for which permission has to be determined
// @param action - Action for which permission has to be determined
// @return allowed - 0 if no access, 1 if access allowed
@view
func get_contract_address{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    index_: felt, version_: felt
) -> (address: felt) {
    let (address) = contract_registry.read(index=index_, version=version_);
    return (address=address);
}

//#####################
// External Functions #
//#####################

// @notice Function to modify trusted contracts registry, only callable by the admins with action access=3
// @param index_ - Index of the registry that needs to be updated
// @param version_ - Version corresponding to the index that needs to be updated
// @param contract_address_ - Contract address for the corresponding index and version
@external
func update_contract_registry{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    index_: felt, version_: felt, contract_address_: felt
) {
    // Auth Check
    let (caller) = get_caller_address();
    let (auth_addr) = contract_registry.read(index=AdminAuth_INDEX, version=version_);
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=ManageAuthRegistry_ACTION
    );

    with_attr error_message("AuthRegistry: Unauthorized call for contract registry updation") {
        assert_not_zero(access);
    }

    // Update the registry
    contract_registry.write(index=index_, version=version_, value=contract_address_);

    updated_registry.emit(index=index_, version=version_, address=contract_address_);
    return ();
}
