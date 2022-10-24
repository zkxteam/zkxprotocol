%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.messages import send_message_to_l1
from starkware.starknet.common.syscalls import get_caller_address

from contracts.Constants import AccountRegistry_INDEX, L1_ZKX_Address_INDEX
from contracts.DataTypes import WithdrawalRequest
from contracts.interfaces.IAccountManager import IAccountManager
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.CommonLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority

//############
// Constants #
//############
const MESSAGE_WITHDRAW = 3;

//#########
// Events #
//#########

// Event emitted whenever add_withdrawal_request() is called
@event
func add_withdrawal_request_called(
    request_id: felt, user_l1_address: felt, ticker: felt, amount: felt, user_l2_address: felt
) {
}

// Event emitted whenever update_withdrawal_request() l1 handler is called
@event
func update_withdrawal_request_called(from_address: felt, user_l2_address: felt, request_id: felt) {
}

//##########
// Storage #
//##########

// Maps request id to withdrawal request
@storage_var
func withdrawal_request_mapping(request_id: felt) -> (res: WithdrawalRequest) {
}

//##############
// Constructor #
//##############

// @notice Constructor of the smart-contract
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    registry_address_: felt, version_: felt
) {
    CommonLib.initialize(registry_address_, version_);
    return ();
}

//#################
// View Functions #
//#################

// @notice Function to get withdrawal request corresponding to the request ID
// @param request_id_ ID of the withdrawal Request
// @return withdrawal_request - returns withdrawal request structure
@view
func get_withdrawal_request_data{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    request_id_: felt
) -> (withdrawal_request: WithdrawalRequest) {
    let (res: WithdrawalRequest) = withdrawal_request_mapping.read(request_id=request_id_);
    return (withdrawal_request=res);
}

//#############
// L1 Handler #
//#############

// @notice Function to handle status updates on withdrawal requests
// @param from_address - The address from where update withdrawal request function is called from
// @param request_id_ - ID of the withdrawal Request
@l1_handler
func update_withdrawal_request{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    from_address: felt, request_id_: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    // Get L1 ZKX contract address
    let (l1_zkx_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=L1_ZKX_Address_INDEX, version=version
    );

    // Make sure the message was sent by the intended L1 contract.
    with_attr error_message("WithdrawalRequest: L1 contract mismatch") {
        assert from_address = l1_zkx_address;
    }

    // get current withdrawal request object according to request_id_
    let current_request: WithdrawalRequest = withdrawal_request_mapping.read(request_id_);

    // get user_l2_address to be used for updating withdrawal history in AccountManager
    let user_l2_address = current_request.user_l2_address;
    assert_not_zero(user_l2_address);
    // Create a struct with the withdrawal Request
    let updated_request = WithdrawalRequest(
        user_l1_address=0, user_l2_address=0, ticker=0, amount=0
    );
    withdrawal_request_mapping.write(request_id=request_id_, value=updated_request);

    // update withdrawal history status field to 1
    IAccountManager.update_withdrawal_history(
        contract_address=user_l2_address, request_id_=request_id_
    );

    // update_withdrawal_request_called event is emitted
    update_withdrawal_request_called.emit(
        from_address=from_address, user_l2_address=user_l2_address, request_id=request_id_
    );

    return ();
}

//#####################
// External Functions #
//#####################

// @notice function to add withdrawal request to the withdrawal request array
// @param request_id_ ID of the withdrawal Request
// @param user_l1_address_ User's L1 wallet address
// @param ticker_ collateral for the requested withdrawal
// @param amount_ Amount to be withdrawn
@external
func add_withdrawal_request{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    request_id_: felt, user_l1_address_: felt, ticker_: felt, amount_: felt
) {
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (caller) = get_caller_address();

    // fetch account registry contract address
    let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    );
    // check whether caller is registered user
    let (present) = IAccountRegistry.is_registered_user(
        contract_address=account_registry_address, address_=caller
    );

    with_attr error_message("WithdrawalRequest: User address not registered") {
        assert_not_zero(present);
    }

    // Create a struct with the withdrawal Request
    let new_request = WithdrawalRequest(
        user_l1_address=user_l1_address_, user_l2_address=caller, ticker=ticker_, amount=amount_
    );

    withdrawal_request_mapping.write(request_id=request_id_, value=new_request);

    // Get L1 ZKX contract address
    let (L1_ZKX_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=L1_ZKX_Address_INDEX, version=version
    );
    // Send the withdrawal message.
    let (message_payload: felt*) = alloc();
    assert message_payload[0] = MESSAGE_WITHDRAW;
    assert message_payload[1] = user_l1_address_;
    assert message_payload[2] = ticker_;
    assert message_payload[3] = amount_;
    assert message_payload[4] = request_id_;

    // Send Message to L1
    send_message_to_l1(to_address=L1_ZKX_contract_address, payload_size=5, payload=message_payload);

    // add_withdrawal_request_called event is emitted
    add_withdrawal_request_called.emit(
        request_id=request_id_,
        user_l1_address=user_l1_address_,
        ticker=ticker_,
        amount=amount_,
        user_l2_address=caller,
    );

    return ();
}
