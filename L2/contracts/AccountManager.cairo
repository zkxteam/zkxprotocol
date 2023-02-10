%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.hash_state import hash_finalize, hash_init, hash_update
from starkware.cairo.common.math import assert_le, assert_nn, assert_not_zero
from starkware.cairo.common.math_cmp import is_le

from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.signature import verify_ecdsa_signature

from starkware.starknet.common.syscalls import (
    emit_event,
    get_block_timestamp,
    get_caller_address,
    get_contract_address,
)

from contracts.Constants import (
    ABR_PAYMENT_INDEX,
    Asset_INDEX,
    BUY,
    DELEVERAGING_ORDER,
    IoC,
    L1_ZKX_Address_INDEX,
    Liquidate_INDEX,
    LIQUIDATION_ORDER,
    LONG,
    Market_INDEX,
    MarketPrices_INDEX,
    OPEN,
    SHORT,
    Trading_INDEX,
    WithdrawalFeeBalance_INDEX,
    WithdrawalRequest_INDEX,
    WITHDRAWAL_INITIATED,
    WITHDRAWAL_SUCCEEDED,
)
from contracts.DataTypes import (
    Asset,
    CollateralBalance,
    LiquidatablePosition,
    Market,
    MarketPrice,
    OrderRequest,
    PositionDetails,
    PositionDetailsForRiskManagement,
    PositionDetailsWithMarket,
    SimplifiedPosition,
    Signature,
    WithdrawalHistory,
    WithdrawalRequestForHashing,
)

from contracts.interfaces.IAccountLiquidator import IAccountLiquidator
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.ILiquidate import ILiquidate
from contracts.interfaces.IMarkets import IMarkets
from contracts.interfaces.IMarketPrices import IMarketPrices
from contracts.interfaces.IWithdrawalFeeBalance import IWithdrawalFeeBalance
from contracts.interfaces.IWithdrawalRequest import IWithdrawalRequest
from contracts.libraries.CommonLibrary import CommonLib
from contracts.Math_64x61 import (
    Math64x61_add,
    Math64x61_assert_le,
    Math64x61_div,
    Math64x61_fromDecimalFelt,
    Math64x61_is_equal,
    Math64x61_is_le,
    Math64x61_min,
    Math64x61_mul,
    Math64x61_round,
    Math64x61_sub,
    Math64x61_toDecimalFelt,
)

// ////////////
// Constants //
// ////////////

const TWO_POINT_FIVE = 5764607523034234880;

// /////////
// Events //
// /////////

// Event emitted whenever a position is marked to be liquidated/deleveraged
@event
func liquidate_deleverage(market_id: felt, direction: felt, amount_to_be_sold: felt) {
}

// //////////
// Storage //
// //////////

// Stores public key associated with an account
@storage_var
func public_key() -> (res: felt) {
}

// Stores balance of an asset
@storage_var
func balance(assetID: felt) -> (res: felt) {
}

// Mapping of marketID, direction to PositionDetails struct
@storage_var
func position_mapping(market_id: felt, direction: felt) -> (res: PositionDetails) {
}

// Mapping of orderID to portionExecuted of that order
@storage_var
func portion_executed(order_id: felt) -> (res: felt) {
}

// Stores L1 address associated with the account
@storage_var
func L1_address() -> (res: felt) {
}

// Stores the mapping from collateral to market_id array
@storage_var
func collateral_to_market_array(collateral_id: felt, index: felt) -> (market_id: felt) {
}

// Stores the length of the collateral to market_id array
@storage_var
func collateral_to_market_array_len(collateral_id: felt) -> (len: felt) {
}

// Stores the mapping from the market_id to index
@storage_var
func market_to_index_mapping(market_id: felt) -> (market_id: felt) {
}

// Stores if a market exists
@storage_var
func market_is_exist(market_id) -> (res: felt) {
}

// Stores all collaterals held by the user
@storage_var
func collateral_array(index: felt) -> (collateral_id: felt) {
}

// Stores length of the collateral array
@storage_var
func collateral_array_len() -> (len: felt) {
}

// Stores the position which is to be deleveraged or liquidated
@storage_var
func deleveragable_or_liquidatable_position(collateral_id: felt) -> (
    position: LiquidatablePosition
) {
}

// Stores all withdrawals made by the user
@storage_var
func withdrawal_history_array(index: felt) -> (res: WithdrawalHistory) {
}

// Stores length of the withdrawal history array
@storage_var
func withdrawal_history_array_len() -> (len: felt) {
}

// Stores the order_id to hash mapping
@storage_var
func order_id_mapping(order_id: felt) -> (hash: felt) {
}

// //////////////
// Constructor //
// //////////////

@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    public_key_: felt, L1_address_: felt, registry_address_: felt, version_: felt
) {
    with_attr error_message("AccountManager: Public key and L1 address cannot be 0") {
        assert_not_zero(public_key_);
        assert_not_zero(L1_address_);
    }

    public_key.write(public_key_);
    L1_address.write(L1_address_);

    CommonLib.initialize(registry_address_, version_);
    return ();
}

// ///////
// View //
// ///////

// @notice view function to get public key
// @return res - public key of an account
@view
func get_public_key{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (res) = public_key.read();
    return (res=res);
}

// @notice view function to check if the transaction signature is valid
// @param hash - Hash of the transaction parameters
// @param singature_len - Length of the signatures
// @param signature - Array of signatures
@view
func is_valid_signature{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*
}(hash: felt, signature_len: felt, signature: felt*) -> () {
    let (_public_key) = public_key.read();

    // This interface expects a signature pointer and length to make
    // no assumption about signature validation schemes.
    // But this implementation does, and it expects a (sig_r, sig_s) pair.
    let sig_r = signature[0];
    let sig_s = signature[1];

    verify_ecdsa_signature(
        message=hash, public_key=_public_key, signature_r=sig_r, signature_s=sig_s
    );

    return ();
}

// @notice view function which checks the signature passed is valid
// @param hash - Hash of the order to check against
// @param signature - Signature passed to the contract to check against
// @param liquidator_address_ - Address of the liquidator
// @return reverts, if there is an error
@view
func is_valid_signature_order{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*
}(hash: felt, signature: Signature, liquidator_address_: felt) -> () {
    alloc_locals;

    let sig_r = signature.r_value;
    let sig_s = signature.s_value;
    local pub_key;

    if (liquidator_address_ != 0) {
        // Verify whether call came from node operator
        let (_public_key) = IAccountLiquidator.getPublicKey(contract_address=liquidator_address_);
        pub_key = _public_key;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    } else {
        let (acc_pub_key) = public_key.read();
        pub_key = acc_pub_key;

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    }

    verify_ecdsa_signature(message=hash, public_key=pub_key, signature_r=sig_r, signature_s=sig_s);
    return ();
}

// @notice view function to get the balance of an asset
// @param assetID_ - ID of an asset
// @return res - balance of an asset
@view
func get_balance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    assetID_: felt
) -> (res: felt) {
    let (res) = balance.read(assetID=assetID_);
    return (res=res);
}

@view
func get_portion_executed{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_id_: felt
) -> (res: felt) {
    let (res) = portion_executed.read(order_id=order_id_);
    return (res=res);
}

// @notice view function to get order details
// @param orderID_ - ID of an order
// @return res - Order details corresponding to an order
@view
func get_position_data{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, direction_: felt
) -> (res: PositionDetails) {
    let (res) = position_mapping.read(market_id=market_id_, direction=direction_);
    return (res=res);
}

// @notice view function to get L1 address of the user
// @return res - L1 address of the user
@view
func get_L1_address{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    res: felt
) {
    let (res) = L1_address.read();
    return (res=res);
}

// @notice view function to get deleveraged or liquidatable position
// @param collateral_id_ - collateral id
// @return position - Returns a LiquidatablePosition struct
@view
func get_deleveragable_or_liquidatable_position{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(collateral_id_: felt) -> (position: LiquidatablePosition) {
    let position = deleveragable_or_liquidatable_position.read(collateral_id=collateral_id_);
    return position;
}

// @notice view function to get all use collaterals
// @return array_list_len - Length of the array_list
// @return array_list - Fully populated list of CollateralBalance
@view
func return_array_collaterals{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    ) -> (array_list_len: felt, array_list: CollateralBalance*) {
    let (array_list: CollateralBalance*) = alloc();
    let (array_len: felt) = collateral_array_len.read();
    return populate_array_collaterals(0, array_list, array_len);
}

// @notice view function to get withdrawal history
// @return withdrawal_list_len - Length of the withdrawal list
// @return withdrawal_list - Fully populated list of withdrawals
@view
func get_withdrawal_history{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    withdrawal_list_len: felt, withdrawal_list: WithdrawalHistory*
) {
    let (withdrawal_list: WithdrawalHistory*) = alloc();
    let (arr_len) = withdrawal_history_array_len.read();
    return populate_withdrawals_array(0, arr_len, withdrawal_list);
}

// @notice view function to get withdrawal history by status
// @param status_ - Withdrawal history status
// @return withdrawal_list_len - Length of the withdrawal list
// @return withdrawal_list - Fully populated list of withdrawals
@view
func get_withdrawal_history_by_status{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(status_: felt) -> (withdrawal_list_len: felt, withdrawal_list: WithdrawalHistory*) {
    let (withdrawal_list: WithdrawalHistory*) = alloc();
    let (arr_len) = withdrawal_history_array_len.read();
    return populate_withdrawals_array_by_status(status_, 0, arr_len, 0, withdrawal_list);
}

// @notice view function to get amount to withdraw
// @param collateral_id_ - ID of the collateral
// @return safe_withdrawal_amount_64x61 - returns the safe amount to withdraw before position gets deleveraged or liquidated
@view
func get_safe_amount_to_withdraw{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    collateral_id_: felt
) -> (safe_withdrawal_amount: felt, withdrawable_amount: felt) {
    alloc_locals;
    local safe_withdrawal_amount_64x61;

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (user_l2_address) = get_contract_address();

    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset: Asset) = IAsset.get_asset(contract_address=asset_address, id=collateral_id_);
    let token_decimals = asset.token_decimal;

    let (current_balance) = balance.read(assetID=collateral_id_);
    let (is_balance_negative) = Math64x61_is_le(current_balance, 0, token_decimals);
    if (is_balance_negative == TRUE) {
        return (0, 0);
    }

    // Get Liquidate contract address
    let (liquidate_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Liquidate_INDEX, version=version
    );
    let (
        liq_result: felt,
        least_collateral_ratio_position: PositionDetailsForRiskManagement,
        total_account_value: felt,
        total_maintenance_requirement: felt,
    ) = ILiquidate.find_under_collateralized_position(
        contract_address=liquidate_address,
        account_address_=user_l2_address,
        collateral_id_=collateral_id_,
    );

    // if TAV <= 0, it means that user is already under water and thus withdrawal is not possible
    let (is_less) = Math64x61_is_le(total_account_value, 0, token_decimals);
    if (is_less == TRUE) {
        return (0, 0);
    }

    // Returns 0, if the position is to be deleveraged or liquiditable
    if (liq_result == 1) {
        assert safe_withdrawal_amount_64x61 = 0;
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        let (safe_amount) = Math64x61_sub(total_account_value, total_maintenance_requirement);
        let (safe_withdrawal_amount_64x61_temp) = Math64x61_min(current_balance, safe_amount);
        if (safe_withdrawal_amount_64x61_temp == current_balance) {
            return (safe_withdrawal_amount_64x61_temp, safe_withdrawal_amount_64x61_temp);
        }
        assert safe_withdrawal_amount_64x61 = safe_withdrawal_amount_64x61_temp;
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    let (withdrawable_amount_64x61) = get_amount_to_withdraw(
        total_account_value,
        total_maintenance_requirement,
        least_collateral_ratio_position,
        collateral_id_,
        token_decimals,
    );
    return (safe_withdrawal_amount_64x61, withdrawable_amount_64x61);
}

// /////////////
// L1 Handler //
// /////////////

// @notice Function to handle deposit from L1ZKX contract
// @param from_address - The address from where deposit function is called from
// @param user - User's Metamask account address
// @param amount - The Amount of funds that user wants to withdraw
// @param assetID_ - Asset ID of the collateral that needs to be deposited
@l1_handler
func deposit{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    from_address: felt, user: felt, amount: felt, assetID_: felt
) {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    // Get L1 ZKX contract address
    let (L1_ZKX_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=L1_ZKX_Address_INDEX, version=version
    );
    // Make sure the message was sent by the intended L1 contract
    with_attr error_message("AccountManager: Unauthorized caller for deposit") {
        assert from_address = L1_ZKX_contract_address;
    }
    let (stored_L1_address) = L1_address.read();
    with_attr error_message("AccountManager: L1 address mismatch for deposit") {
        assert stored_L1_address = user;
    }
    // Get asset contract address
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    // Converting asset amount to Math64x61 format
    let (asset: Asset) = IAsset.get_asset(contract_address=asset_address, id=assetID_);
    let (amount_in_decimal_representation) = Math64x61_fromDecimalFelt(
        amount, decimals=asset.token_decimal
    );
    let (array_len) = collateral_array_len.read();
    // Read the current balance.
    let (balance_collateral) = balance.read(assetID=assetID_);
    let (is_equal) = Math64x61_is_equal(balance_collateral, 0, asset.token_decimal);
    if (is_equal == TRUE) {
        add_collateral(new_asset_id=assetID_, iterator=0, length=array_len);
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }
    // Compute and update the new balance.
    tempvar new_balance = balance_collateral + amount_in_decimal_representation;
    balance.write(assetID=assetID_, value=new_balance);

    let (keys: felt*) = alloc();
    assert keys[0] = 'deposit';
    let (data: felt*) = alloc();
    assert data[0] = amount;
    assert data[1] = balance_collateral;
    assert data[2] = assetID_;
    assert data[3] = user;

    emit_event(1, keys, 4, data);
    return ();
}

// ///////////
// External //
// ///////////

// @notice External function called by the Trading Contract
// @param assetID_ - asset ID of the collateral that needs to be transferred
// @param amount - Amount of funds to transfer from this contract
@external
func transfer_from{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    assetID_: felt, amount_: felt, invoked_for_: felt
) -> () {
    // Check if the caller is trading contract
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    );

    with_attr error_message("AccountManager: Unauthorized caller for transfer_from") {
        assert caller = trading_address;
    }

    with_attr error_message("AccountManager: Amount cannot be negative") {
        assert_nn(amount_);
    }

    let (balance_) = balance.read(assetID=assetID_);
    let (new_balance) = Math64x61_sub(balance_, amount_);
    balance.write(assetID=assetID_, value=new_balance);

    let (keys: felt*) = alloc();
    assert keys[0] = invoked_for_;
    let (data: felt*) = alloc();
    assert data[0] = -amount_;
    assert data[1] = balance_;
    assert data[2] = assetID_;

    emit_event(1, keys, 3, data);

    return ();
}

// @notice External function called by the Trading Contract to transfer funds from account contract
// @param assetID_ - asset ID of the collateral that needs to be transferred
// @param amount - Amount of funds to transfer to this contract
@external
func transfer{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    assetID_: felt, amount_: felt, invoked_for_: felt
) -> () {
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    );
    with_attr error_message("AccountManager: Unauthorized caller for transfer") {
        assert caller = trading_address;
    }

    with_attr error_message("AccountManager: Amount cannot be negative") {
        assert_nn(amount_);
    }

    let (balance_) = balance.read(assetID=assetID_);
    let (new_balance) = Math64x61_add(balance_, amount_);
    balance.write(assetID=assetID_, value=new_balance);

    let (keys: felt*) = alloc();
    assert keys[0] = invoked_for_;
    let (data: felt*) = alloc();
    assert data[0] = amount_;
    assert data[1] = balance_;
    assert data[2] = assetID_;

    emit_event(1, keys, 3, data);

    return ();
}

// @notice External function called by the ABR Payment contract
// @param collateral_id_ - Collateral ID of the position
// @param market_id_ - Market ID of the position
// @param amount - Amount of funds to transfer from this contract
@external
func transfer_from_abr{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    collateral_id_: felt,
    market_id_: felt,
    direction_: felt,
    amount_: felt,
    abr_value_: felt,
    position_size_: felt,
) {
    // Check if the caller is ABR Payment
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (abr_payment_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_PAYMENT_INDEX, version=version
    );

    with_attr error_message("AccountManager: Unauthorized caller for transfer_from_abr") {
        assert caller = abr_payment_address;
    }

    with_attr error_message("AccountManager: Amount cannot be negative") {
        assert_le(0, amount_);
    }

    // Reduce the amount from balance
    let (balance_) = balance.read(assetID=collateral_id_);
    let (new_balance) = Math64x61_sub(balance_, amount_);
    balance.write(assetID=collateral_id_, value=new_balance);

    // Get curent block_timestamp
    let (block_timestamp) = get_block_timestamp();

    // Get the details of the position
    let (position_details: PositionDetails) = position_mapping.read(
        market_id=market_id_, direction=direction_
    );

    // Calculate the new pnl
    let (new_realized_pnl) = Math64x61_sub(position_details.realized_pnl, amount_);

    // Create a new struct with the updated details
    let updated_position = PositionDetails(
        avg_execution_price=position_details.avg_execution_price,
        position_size=position_details.position_size,
        margin_amount=position_details.margin_amount,
        borrowed_amount=position_details.borrowed_amount,
        leverage=position_details.leverage,
        created_timestamp=position_details.created_timestamp,
        modified_timestamp=block_timestamp,
        realized_pnl=new_realized_pnl,
    );

    // Write it to the position mapping
    position_mapping.write(market_id=market_id_, direction=direction_, value=updated_position);

    let (keys: felt*) = alloc();
    assert keys[0] = 'abr_transfer';
    let (data: felt*) = alloc();
    assert data[0] = -amount_;
    assert data[1] = balance_;
    assert data[2] = collateral_id_;
    assert data[3] = market_id_;
    assert data[4] = abr_value_;
    assert data[5] = position_size_;

    emit_event(1, keys, 6, data);

    return ();
}

// @notice External function called by the ABR Payment contract
// @param collateral_id_ - Collateral ID of the position
// @param market_id_ - Market ID of the position
// @param amount_ - Amount of funds to transfer from this contract
@external
func transfer_abr{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    collateral_id_: felt,
    market_id_: felt,
    direction_: felt,
    amount_: felt,
    abr_value_: felt,
    position_size_: felt,
) {
    // Check if the caller is trading contract
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (abr_payment_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_PAYMENT_INDEX, version=version
    );
    with_attr error_message("AccountManager: Unauthorized caller for transfer_abr") {
        assert caller = abr_payment_address;
    }

    with_attr error_message("AccountManager: Amount cannot be negative") {
        assert_le(0, amount_);
    }

    // Add amount to balance
    let (balance_) = balance.read(assetID=collateral_id_);
    let (new_balance) = Math64x61_add(balance_, amount_);
    balance.write(assetID=collateral_id_, value=new_balance);

    // Update the timestamp of last called
    let (block_timestamp) = get_block_timestamp();

    // Get the details of the position
    let (position_details: PositionDetails) = position_mapping.read(
        market_id=market_id_, direction=direction_
    );

    // Calculate the new pnl
    let (new_realized_pnl) = Math64x61_add(position_details.realized_pnl, amount_);

    // Create a new struct with the updated details
    let updated_position = PositionDetails(
        avg_execution_price=position_details.avg_execution_price,
        position_size=position_details.position_size,
        margin_amount=position_details.margin_amount,
        borrowed_amount=position_details.borrowed_amount,
        leverage=position_details.leverage,
        created_timestamp=position_details.created_timestamp,
        modified_timestamp=block_timestamp,
        realized_pnl=new_realized_pnl,
    );

    // Write it to the position mapping
    position_mapping.write(market_id=market_id_, direction=direction_, value=updated_position);

    let (keys: felt*) = alloc();
    assert keys[0] = 'abr_transfer';
    let (data: felt*) = alloc();
    assert data[0] = amount_;
    assert data[1] = balance_;
    assert data[2] = collateral_id_;
    assert data[3] = market_id_;
    assert data[4] = abr_value_;
    assert data[5] = position_size_;

    emit_event(1, keys, 6, data);

    return ();
}

// @notice External function called by the ABR Contract to get the array of positions of the user filtered by timestamp
// @param timestmap_filter_ - Timestamp by which to filter the array
// @returns positions_array_len - Length of the array
// @returns positions_array - Required array of net positions
@view
func get_simplified_positions{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    timestamp_filter_: felt
) -> (positions_array_len: felt, positions_array: SimplifiedPosition*) {
    alloc_locals;

    let (positions_array: SimplifiedPosition*) = alloc();
    let (collateral_array_len_) = collateral_array_len.read();
    return populate_simplified_positions_collaterals_recurse(
        positions_array_len_=0,
        positions_array_=positions_array,
        collateral_array_iterator_=0,
        collateral_array_len_=collateral_array_len_,
        timestamp_filter_=timestamp_filter_,
    );
}

// @notice External function called by the Liquidate Contract to get the array of net positions of the user
// @param collateral_id_ - collateral id
// @returns positions_array_len - Length of the array
// @returns positions_array - Required array of positions
@view
func get_positions_for_risk_management{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(collateral_id_: felt) -> (
    positions_array_len: felt, positions_array: PositionDetailsForRiskManagement*
) {
    alloc_locals;

    let (positions_array: PositionDetailsForRiskManagement*) = alloc();
    let (markets_array_len: felt) = collateral_to_market_array_len.read(
        collateral_id=collateral_id_
    );
    return populate_positions_risk_management(
        collateral_id_=collateral_id_,
        positions_array_len_=0,
        positions_array_=positions_array,
        iterator_=0,
        markets_array_len_=markets_array_len,
    );
}

// @notice External function called by the Liquidate Contract to get the array of net positions of the user
// @returns positions_array_len - Length of the array
// @returns positions_array - Required array of positions
@view
func get_positions{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() -> (
    positions_array_len: felt, positions_array: PositionDetailsWithMarket*
) {
    alloc_locals;

    let (positions_array: PositionDetailsWithMarket*) = alloc();
    let (collateral_array_len_) = collateral_array_len.read();
    return populate_positions_collaterals_recurse(
        positions_array_len_=0,
        positions_array_=positions_array,
        collateral_array_iterator_=0,
        collateral_array_len_=collateral_array_len_,
    );
}

// @notice Function called by Trading Contract
// @param request - Details of the order to be executed
// @param signature - Details of the signature
// @param size - Size of the Order to be executed
// @param execution_price - Price at which the order should be executed
// @param margin_amount - New margin amount of the position
// @param borrowed_amount - New borrowed amount of the position
// @param market_id - Market id of the position
// @param collateral_id_ - Collateral id of the position
// @param pnl_ - New pnl of the position
// @return 1, if executed correctly
@external
func execute_order{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*
}(
    request: OrderRequest,
    signature: Signature,
    size: felt,
    execution_price: felt,
    margin_amount: felt,
    borrowed_amount: felt,
    market_id: felt,
    collateral_id_: felt,
    pnl: felt,
    side: felt,
) -> (res: felt) {
    alloc_locals;

    local order_id;
    assert order_id = request.order_id;

    let (__fp__, _) = get_fp_and_pc();

    // Make sure that the caller is the authorized Trading Contract
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (trading_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Trading_INDEX, version=version
    );
    with_attr error_message("0002: {order_id} {market_id}") {
        assert caller = trading_address;
    }

    // Get asset and collateral number of decimals
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );
    let (market: Market) = IMarkets.get_market(
        contract_address=market_address, market_id_=market_id
    );
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset_details) = IAsset.get_asset(contract_address=asset_address, id=market.asset);
    let asset_decimals = asset_details.token_decimal;

    // hash the parameters
    let (hash) = hash_order(&request);

    // Check for hash collision
    order_hash_check(request.order_id, hash);

    // check if signed by the user/liquidator
    is_valid_signature_order(hash, signature, request.liquidator_address);

    // Get the details of the position
    let (position_details: PositionDetails) = position_mapping.read(
        market_id=market_id, direction=request.direction
    );

    // Get the portion executed details if already exists
    let (order_portion_executed) = portion_executed.read(order_id=request.order_id);
    let (new_position_executed) = Math64x61_add(order_portion_executed, size);

    // Return if the position size after the executing the current order is more than the order's positionSize
    with_attr error_message("0001: {order_id} {size}") {
        Math64x61_assert_le(new_position_executed, request.quantity, asset_decimals);
    }

    if (request.time_in_force == IoC) {
        // Update the portion executed to request.quantity if it's an IoC order
        portion_executed.write(order_id=request.order_id, value=request.quantity);
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
    } else {
        // Update the portion executed
        portion_executed.write(order_id=request.order_id, value=new_position_executed);
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
    }
    tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;

    let (local current_timestamp) = get_block_timestamp();

    // closeOrder == 1 -> Open a new position
    // closeOrder == 2 -> Close a position
    if (request.side == BUY) {
        local created_timestamp;
        let (is_equal) = Math64x61_is_equal(position_details.position_size, 0, asset_decimals);
        if (is_equal == TRUE) {
            add_to_market_array(market_id_=market_id, collateral_id_=collateral_id_);
            created_timestamp = current_timestamp;
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            created_timestamp = position_details.created_timestamp;
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }

        // New position size
        let (new_position_size) = Math64x61_add(position_details.position_size, size);

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        // New leverage
        let (total_value) = Math64x61_add(margin_amount, borrowed_amount);
        let (new_leverage) = Math64x61_div(total_value, margin_amount);
        let (new_leverage_rounded) = Math64x61_round(new_leverage, 5);
        let (current_pnl: felt) = Math64x61_add(position_details.realized_pnl, pnl);

        // Create a new struct with the updated details
        let updated_position = PositionDetails(
            avg_execution_price=execution_price,
            position_size=new_position_size,
            margin_amount=margin_amount,
            borrowed_amount=borrowed_amount,
            leverage=new_leverage_rounded,
            created_timestamp=created_timestamp,
            modified_timestamp=current_timestamp,
            realized_pnl=current_pnl,
        );

        // Write to the mapping
        position_mapping.write(
            market_id=market_id, direction=request.direction, value=updated_position
        );

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    } else {
        // Calculate the new leverage if it's a deleveraging order
        local new_leverage;

        // Get the current position details
        let (current_position_details) = position_mapping.read(
            market_id=market_id, direction=request.direction
        );
        let (new_position_size) = Math64x61_sub(current_position_details.position_size, size);

        // Assert that the size amount can be closed from the existing position
        with_attr error_message("0003: {order_id} {size}") {
            Math64x61_assert_le(0, new_position_size, asset_decimals);
        }

        // Check if it's liq/delveraging order
        let is_liq = is_le(LIQUIDATION_ORDER, request.order_type);

        if (is_liq == 1) {
            // If it's not a normal order, check if it satisfies the conditions to liquidate/deleverage
            let liq_position: LiquidatablePosition = deleveragable_or_liquidatable_position.read(
                collateral_id=collateral_id_
            );

            with_attr error_message("0004: {order_id} {market_id}") {
                assert liq_position.market_id = market_id;
                assert liq_position.direction = request.direction;
            }

            with_attr error_message("0005: {order_id} {size}") {
                Math64x61_assert_le(size, liq_position.amount_to_be_sold, asset_decimals);
            }

            let (updated_amount) = Math64x61_sub(liq_position.amount_to_be_sold, size);

            local updated_liquidatable_position: LiquidatablePosition;
            let (is_equal_zero) = Math64x61_is_equal(updated_amount, 0, 6);  // Double check precision
            if (is_equal_zero == TRUE) {
                assert updated_liquidatable_position = LiquidatablePosition(
                    market_id=0, direction=0, amount_to_be_sold=0, liquidatable=0
                );
            } else {
                assert updated_liquidatable_position = LiquidatablePosition(
                    market_id=liq_position.market_id,
                    direction=liq_position.direction,
                    amount_to_be_sold=updated_amount,
                    liquidatable=liq_position.liquidatable,
                );
            }

            // Update the Liquidatable position
            deleveragable_or_liquidatable_position.write(
                collateral_id=collateral_id_, value=updated_liquidatable_position
            );

            // If it's a deleveraging order, calculate the new leverage
            if (request.order_type == DELEVERAGING_ORDER) {
                with_attr error_message("0007: {order_id} {size}") {
                    assert liq_position.liquidatable = FALSE;
                }
                let total_value = margin_amount + borrowed_amount;
                let (leverage_) = Math64x61_div(total_value, margin_amount);
                assert new_leverage = leverage_;
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            } else {
                with_attr error_message("0006: {order_id} {size}") {
                    assert liq_position.liquidatable = TRUE;
                }

                assert new_leverage = current_position_details.leverage;
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }
        } else {
            assert new_leverage = current_position_details.leverage;
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;

        let (is_equal) = Math64x61_is_equal(new_position_size, 0, asset_decimals);
        if (is_equal == TRUE) {
            if (position_details.position_size == 0) {
                remove_from_market_array(market_id_=market_id, collateral_id_=collateral_id_);
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            } else {
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }

            // Write to the mapping
            position_mapping.write(
                market_id=market_id,
                direction=request.direction,
                value=PositionDetails(
                    avg_execution_price=0,
                    position_size=0,
                    margin_amount=0,
                    borrowed_amount=0,
                    leverage=0,
                    created_timestamp=0,
                    modified_timestamp=0,
                    realized_pnl=0,
                ),
            );

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            let (current_pnl: felt) = Math64x61_add(current_position_details.realized_pnl, pnl);

            // Create a new struct with the updated details
            let updated_position = PositionDetails(
                avg_execution_price=execution_price,
                position_size=new_position_size,
                margin_amount=margin_amount,
                borrowed_amount=borrowed_amount,
                leverage=new_leverage,
                created_timestamp=current_position_details.created_timestamp,
                modified_timestamp=current_timestamp,
                realized_pnl=current_pnl,
            );

            position_mapping.write(
                market_id=market_id, direction=request.direction, value=updated_position
            );

            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }

        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
        tempvar ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    }

    // Emit event for the order
    let (keys: felt*) = alloc();
    assert keys[0] = 'trade';
    let (data: felt*) = alloc();
    assert data[0] = order_id;
    assert data[1] = market_id;
    assert data[2] = request.direction;
    assert data[3] = request.quantity;
    assert data[4] = request.order_type;
    assert data[5] = execution_price;
    assert data[6] = pnl;
    assert data[7] = side;

    emit_event(1, keys, 8, data);

    return (1,);
}

// @notice function to update l1 fee and node operators l1 wallet address
// @param request_id_ - Id of the withdrawal request
@external
func update_withdrawal_history{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*
}(request_id_: felt) {
    alloc_locals;
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    // Get asset contract address
    let (withdrawal_request_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=WithdrawalRequest_INDEX, version=version
    );
    with_attr error_message("AccountManager: Unauthorized caller for withdrawal history updation") {
        assert caller = withdrawal_request_address;
    }
    let (arr_len) = withdrawal_history_array_len.read();
    let (index) = find_index_to_be_updated_recurse(request_id_, arr_len);
    local index_to_be_updated = index;
    if (index_to_be_updated != -1) {
        let (history) = withdrawal_history_array.read(index=index_to_be_updated);
        let updated_history = WithdrawalHistory(
            request_id=history.request_id,
            collateral_id=history.collateral_id,
            amount=history.amount,
            timestamp=history.timestamp,
            node_operator_L2_address=history.node_operator_L2_address,
            fee=history.fee,
            status=WITHDRAWAL_SUCCEEDED,
        );
        withdrawal_history_array.write(index=index_to_be_updated, value=updated_history);
        return ();
    }
    return ();
}

// @notice Function to withdraw funds
// @param request_id_ - Id of the withdrawal request
// @param collateral_id_ - Id of the collateral on which user submitted withdrawal request
// @param amount_ - Amount of funds that user wants to withdraw
// @param sig_r_ - R part of signature
// @param sig_s_ - S part of signature
// @param node_operator_L2_address_ - Node operators L2 address
@external
func withdraw{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, ecdsa_ptr: SignatureBuiltin*
}(
    request_id_: felt,
    collateral_id_: felt,
    amount_: felt,
    sig_r_: felt,
    sig_s_: felt,
    node_operator_L2_address_: felt,
) {
    alloc_locals;
    let (__fp__, _) = get_fp_and_pc();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (signature_: felt*) = alloc();
    assert signature_[0] = sig_r_;
    assert signature_[1] = sig_s_;
    // Create withdrawal request for hashing
    local hash_withdrawal_request_: WithdrawalRequestForHashing = WithdrawalRequestForHashing(
        request_id=request_id_, collateral_id=collateral_id_, amount=amount_
    );
    // hash the parameters
    let (hash) = hash_withdrawal_request(&hash_withdrawal_request_);
    // check if Tx is signed by the user
    is_valid_signature(hash, 2, signature_);
    let (arr_len) = withdrawal_history_array_len.read();
    let (result) = check_for_withdrawal_replay(request_id_, arr_len);
    with_attr error_message("AccountManager: Withdrawal replay detected") {
        assert_nn(result);
    }
    // Make sure 'amount' is positive.
    with_attr error_message("AccountManager: Amount cannot be negative") {
        assert_nn(amount_);
    }
    // get L2 Account contract address
    let (user_l2_address) = get_contract_address();
    // Update the fees to be paid by user in withdrawal fee balance contract
    let (withdrawal_fee_balance_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=WithdrawalFeeBalance_INDEX, version=version
    );
    let (standard_fee, fee_collateral_id) = IWithdrawalFeeBalance.get_standard_withdraw_fee(
        contract_address=withdrawal_fee_balance_address
    );

    // Compute current balance
    let (fee_collateral_balance) = balance.read(assetID=fee_collateral_id);
    with_attr error_message("AccountManager: Insufficient balance to pay fees") {
        assert_le(standard_fee, fee_collateral_balance);
    }
    let (new_fee_collateral_balance) = Math64x61_sub(fee_collateral_balance, standard_fee);
    // Update the new fee collateral balance
    balance.write(assetID=fee_collateral_id, value=new_fee_collateral_balance);
    IWithdrawalFeeBalance.update_withdrawal_fee_mapping(
        contract_address=withdrawal_fee_balance_address,
        collateral_id_=fee_collateral_id,
        fee_to_add_=standard_fee,
    );

    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset: Asset) = IAsset.get_asset(contract_address=asset_address, id=collateral_id_);

    // Check whether any position is already marked to be deleveraged or liquidatable
    let (position: LiquidatablePosition) = deleveragable_or_liquidatable_position.read(
        collateral_id_
    );
    with_attr error_message(
            "AccountManager: This withdrawal will lead to either deleveraging or liquidation") {
        assert position.liquidatable = 0;
        assert position.amount_to_be_sold = 0;
    }

    // Check whether the withdrawal leads to the position to be liquidatable or deleveraged
    let (_, withdrawable_amount) = get_safe_amount_to_withdraw(collateral_id_);

    with_attr error_message(
            "AccountManager: This withdrawal will lead to either deleveraging or liquidation") {
        Math64x61_assert_le(amount_, withdrawable_amount, asset.token_decimal);
    }

    // Compute current balance
    let (current_balance) = balance.read(assetID=collateral_id_);
    let (new_balance) = Math64x61_sub(current_balance, amount_);
    // Update the new balance
    balance.write(assetID=collateral_id_, value=new_balance);

    // Calculate the timestamp
    let (timestamp_) = get_block_timestamp();

    // Convert amount from Math64x61 format to felt
    let (amount_in_felt) = Math64x61_toDecimalFelt(amount_, decimals=asset.token_decimal);
    // Get the L1 wallet address of the user
    let (user_l1_address) = L1_address.read();
    // Add Withdrawal Request to WithdrawalRequest Contract
    let (withdrawal_request_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=WithdrawalRequest_INDEX, version=version
    );
    IWithdrawalRequest.add_withdrawal_request(
        contract_address=withdrawal_request_address,
        request_id_=request_id_,
        user_l1_address_=user_l1_address,
        asset_id_=asset.id,
        amount_=amount_in_felt,
    );
    // Create a withdrawal history object
    local withdrawal_history_: WithdrawalHistory = WithdrawalHistory(
        request_id=request_id_,
        collateral_id=collateral_id_,
        amount=amount_,
        timestamp=timestamp_,
        node_operator_L2_address=node_operator_L2_address_,
        fee=standard_fee,
        status=WITHDRAWAL_INITIATED,
    );
    // Update Withdrawal history
    let (array_len) = withdrawal_history_array_len.read();
    withdrawal_history_array.write(index=array_len, value=withdrawal_history_);
    withdrawal_history_array_len.write(array_len + 1);

    // Event for withdrawal
    let (keys: felt*) = alloc();
    assert keys[0] = 'withdrawal';
    let (data: felt*) = alloc();
    assert data[0] = -amount_;
    assert data[1] = current_balance;
    assert data[2] = collateral_id_;
    assert data[3] = user_l1_address;

    emit_event(1, keys, 4, data);

    // Event for withdrawal fee
    let (keys: felt*) = alloc();
    assert keys[0] = 'withdrawal_fee';
    let (data: felt*) = alloc();
    assert data[0] = -standard_fee;
    assert data[1] = fee_collateral_balance;
    assert data[2] = fee_collateral_id;

    emit_event(1, keys, 3, data);

    return ();
}

// @notice Function called by liquidate contract to mark the position as liquidated/deleveraged
// @param position_ - Order Id of the position to be marked
// @param amount_to_be_sold_ - Amount to be put on sale for deleveraging a position
@external
func liquidate_position{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    collateral_id_: felt, position_: PositionDetailsForRiskManagement, amount_to_be_sold_: felt
) {
    alloc_locals;

    // Check if the caller is the liquidator contract
    let (caller) = get_caller_address();
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (liquidate_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Liquidate_INDEX, version=version
    );

    with_attr error_message("AccountManager: Unauthorized caller for liquidate_position") {
        assert caller = liquidate_address;
    }

    local amount;
    local liquidatable;
    if (amount_to_be_sold_ == 0) {
        assert amount = position_.position_size;
        assert liquidatable = TRUE;
    } else {
        assert amount = amount_to_be_sold_;
        assert liquidatable = FALSE;
    }

    let liquidatable_position: LiquidatablePosition = LiquidatablePosition(
        market_id=position_.market_id,
        direction=position_.direction,
        amount_to_be_sold=amount,
        liquidatable=liquidatable,
    );

    // Update deleveraged or liquidatable position
    deleveragable_or_liquidatable_position.write(
        collateral_id=collateral_id_, value=liquidatable_position
    );

    liquidate_deleverage.emit(
        market_id=position_.market_id, direction=position_.direction, amount_to_be_sold=amount
    );
    return ();
}

// ///////////
// Internal //
// ///////////

// @notice Internal function to calculate maximum amount withdrawable by user which will not result in liquidation
// Withdrawing this amount may result in deleveraging
// @param total_account_value - current total account value including all positions and balance
// @param total_maintenance_requirement - current total maintenance requirement for all positions
// @param least_collateral_ratio_position - details of position with least collateral ratio
// @return withdrawable_amount - amount that can be withdrawn by the user
func get_amount_to_withdraw{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    total_account_value_: felt,
    total_maintenance_requirement_: felt,
    least_collateral_ratio_position_: PositionDetailsForRiskManagement,
    collateral_id_: felt,
    token_decimals_: felt,
) -> (withdrawable_amount: felt) {
    alloc_locals;

    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

    let (current_balance) = balance.read(assetID=collateral_id_);

    // This function will only be called in these cases:
    // i) if TAV < TMR ii) if (TAV - TMR) < balance
    // we calculate maximum amount that can be sold so that the position won't get liquidated
    // calculate new TAV and new TMR to get maximum withdrawable amount
    // amount_to_sell = initial_size - ((2.5 * margin_amount)/current_asset_price)
    let (market_price_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=MarketPrices_INDEX, version=version
    );
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );
    let (market_price: MarketPrice) = IMarketPrices.get_market_price(
        contract_address=market_price_address, id=least_collateral_ratio_position_.market_id
    );

    // Validate that the market price is still under TTL
    let (market_ttl: felt) = IMarkets.get_ttl_from_market(
        contract_address=market_address, market_id_=least_collateral_ratio_position_.market_id
    );
    let (current_timestamp) = get_block_timestamp();
    let ttl = market_ttl;
    let timestamp = market_price.timestamp;
    let time_difference = current_timestamp - timestamp;
    let status = is_le(time_difference, ttl);
    // ttl has passed, which means market price is not valid anymore
    if (status == FALSE) {
        return (current_balance,);
    }

    let (min_leverage_times_margin) = Math64x61_mul(
        TWO_POINT_FIVE, least_collateral_ratio_position_.margin_amount
    );
    let (new_size) = Math64x61_div(min_leverage_times_margin, market_price.price);

    // calculate account value and maintenance requirement of least collateral position before reducing size
    let (account_value_initial) = Math64x61_mul(
        least_collateral_ratio_position_.position_size, market_price.price
    );
    let (req_margin) = IMarkets.get_maintenance_margin(
        contract_address=market_address, market_id_=least_collateral_ratio_position_.market_id
    );
    let (leveraged_position_value_initial) = Math64x61_mul(
        least_collateral_ratio_position_.position_size,
        least_collateral_ratio_position_.avg_execution_price,
    );
    let (maintenance_requirement_initial) = Math64x61_mul(
        req_margin, leveraged_position_value_initial
    );

    // calculate account value and maintenance requirement of least collateral position after reducing size
    let (account_value_after) = Math64x61_mul(new_size, market_price.price);
    let (leveraged_position_value_after) = Math64x61_mul(
        new_size, least_collateral_ratio_position_.avg_execution_price
    );
    let (maintenance_requirement_after) = Math64x61_mul(req_margin, leveraged_position_value_after);

    // calculate new TAV and new TMR after reducing size
    let (account_value_difference) = Math64x61_sub(account_value_after, account_value_initial);
    let (maintenance_requirement_difference) = Math64x61_sub(
        maintenance_requirement_after, maintenance_requirement_initial
    );
    let (new_tav) = Math64x61_add(total_account_value_, account_value_difference);
    let (new_tmr) = Math64x61_add(
        total_maintenance_requirement_, maintenance_requirement_difference
    );

    let (new_sub_result) = Math64x61_sub(new_tav, new_tmr);
    let (is_new_tav_greater) = Math64x61_is_le(current_balance, new_sub_result, token_decimals_);
    if (is_new_tav_greater == TRUE) {
        return (current_balance,);
    } else {
        return (new_sub_result,);
    }
}

// @notice Internal Function called by get_withdrawal_history to recursively add WithdrawalRequest to the array and return it
// @param iterator_ - Index to fetch withdrawal history
// @param withdrawal_list_len_ - Stores the current length of the populated withdrawals array
// @param withdrawal_list_ - Array of WithdrawalRequest filled up to the index
// @return withdrawal_list_len - Length of the withdrawal_list
// @return withdrawal_list - Fully populated list of Withdrawals
func populate_withdrawals_array{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    iterator_: felt, withdrawal_list_len_: felt, withdrawal_list_: WithdrawalHistory*
) -> (withdrawal_list_len: felt, withdrawal_list: WithdrawalHistory*) {
    if (iterator_ == withdrawal_list_len_) {
        return (withdrawal_list_len_, withdrawal_list_);
    }

    let (withdrawal_history) = withdrawal_history_array.read(index=iterator_);
    assert withdrawal_list_[iterator_] = withdrawal_history;
    return populate_withdrawals_array(iterator_ + 1, withdrawal_list_len_, withdrawal_list_);
}

// @notice Internal Function called by get_withdrawal_history_by_status to recursively add WithdrawalRequest to the array and return it
// @param status_ - Status of the withdrawal
// @param iterator_ - Index to fetch withdrawal history
// @param withdrawal_array_len_ - Length of withdrawals array
// @param withdrawal_list_len_ - Stores the current length of the populated withdrawals array
// @param withdrawal_list_ - Array of WithdrawalRequest filled up to the index
// @return withdrawal_list_len - Length of the withdrawal_list
// @return withdrawal_list - Fully populated list of Withdrawals
func populate_withdrawals_array_by_status{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    status_: felt,
    iterator_: felt,
    withdrawal_array_len_: felt,
    withdrawal_list_len_: felt,
    withdrawal_list_: WithdrawalHistory*,
) -> (withdrawal_list_len: felt, withdrawal_list: WithdrawalHistory*) {
    alloc_locals;
    if (iterator_ == withdrawal_array_len_) {
        return (withdrawal_list_len_, withdrawal_list_);
    }

    local withdrawal_list_len;
    let (withdrawal_history) = withdrawal_history_array.read(index=iterator_);
    if (withdrawal_history.status == status_) {
        assert withdrawal_list_[withdrawal_list_len_] = withdrawal_history;
        withdrawal_list_len = withdrawal_list_len_ + 1;
    } else {
        withdrawal_list_len = withdrawal_list_len_;
    }

    return populate_withdrawals_array_by_status(
        status_, iterator_ + 1, withdrawal_array_len_, withdrawal_list_len, withdrawal_list_
    );
}

// @notice Internal Function called by return_array_collaterals to recursively add collateralBalance to the array and return it
// @param array_list_len_ - Stores the current length of the populated array
// @param array_list_ - Array of CollateralBalance filled up to the index
// @return array_list_len - Length of the array_list
// @return array_list - Fully populated list of CollateralBalance
func populate_array_collaterals{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    array_list_len_: felt, array_list_: CollateralBalance*, final_len_
) -> (array_list_len: felt, array_list: CollateralBalance*) {
    if (array_list_len_ == final_len_) {
        return (array_list_len_, array_list_);
    }

    let (collateral_id) = collateral_array.read(index=array_list_len_);
    let (collateral_balance: felt) = balance.read(assetID=collateral_id);
    let collateral_balance_struct = CollateralBalance(
        assetID=collateral_id, balance=collateral_balance
    );

    assert array_list_[array_list_len_] = collateral_balance_struct;
    return populate_array_collaterals(array_list_len_ + 1, array_list_, final_len_);
}

// @notice Internal Function called by get_positions_for_risk_management to recursively add active positions to the array and return it
// @param collateral_id_ - collateral id
// @param positions_array_len_ - Length of the array
// @param positions_array_ - Required array of positions
// @param iterator_ - Current length of traversed array
// @param markets_array_len_ - Length of the markets array
// @returns positions_array_len - Length of the positions array
// @returns positions_array - Array with the positions
func populate_positions_risk_management{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    collateral_id_: felt,
    positions_array_len_: felt,
    positions_array_: PositionDetailsForRiskManagement*,
    iterator_: felt,
    markets_array_len_: felt,
) -> (positions_array_len: felt, positions_array: PositionDetailsForRiskManagement*) {
    alloc_locals;

    // If we reached the end of the array, then return
    if (markets_array_len_ == iterator_) {
        return (positions_array_len_, positions_array_);
    }

    // Get the market id at that position
    let (curr_market_id: felt) = collateral_to_market_array.read(
        collateral_id=collateral_id_, index=iterator_
    );

    // Get Long position
    let (long_position: PositionDetails) = position_mapping.read(
        market_id=curr_market_id, direction=LONG
    );

    // Get Short position
    let (short_position: PositionDetails) = position_mapping.read(
        market_id=curr_market_id, direction=SHORT
    );

    // Get asset token decimal
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );
    let (market: Market) = IMarkets.get_market(
        contract_address=market_address, market_id_=curr_market_id
    );
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset: Asset) = IAsset.get_asset(contract_address=asset_address, id=market.asset);

    local is_long;
    local is_short;

    let (is_long_zero) = Math64x61_is_equal(long_position.position_size, 0, asset.token_decimal);
    if (is_long_zero == TRUE) {
        assert is_long = 0;
    } else {
        // Store it in the array
        let curr_position = PositionDetailsForRiskManagement(
            market_id=curr_market_id,
            direction=LONG,
            avg_execution_price=long_position.avg_execution_price,
            position_size=long_position.position_size,
            margin_amount=long_position.margin_amount,
            borrowed_amount=long_position.borrowed_amount,
            leverage=long_position.leverage,
        );
        assert positions_array_[positions_array_len_] = curr_position;
        assert is_long = 1;
    }

    let (is_short_zero) = Math64x61_is_equal(short_position.position_size, 0, asset.token_decimal);
    if (is_short_zero == TRUE) {
        assert is_short = 0;
    } else {
        // Store it in the array
        let curr_position = PositionDetailsForRiskManagement(
            market_id=curr_market_id,
            direction=SHORT,
            avg_execution_price=short_position.avg_execution_price,
            position_size=short_position.position_size,
            margin_amount=short_position.margin_amount,
            borrowed_amount=short_position.borrowed_amount,
            leverage=long_position.leverage,
        );
        assert positions_array_[positions_array_len_ + is_long] = curr_position;
        assert is_short = 1;
    }

    return populate_positions_risk_management(
        collateral_id_=collateral_id_,
        positions_array_len_=positions_array_len_ + is_long + is_short,
        positions_array_=positions_array_,
        iterator_=iterator_ + 1,
        markets_array_len_=markets_array_len_,
    );
}

// @notice Internal Function called by get_positions to recursively add active positions to the array and return it
// @param positions_array_len_ - Length of the array
// @param positions_array_ - Required array of positions
// @param markets_iterator_ - Current length of traversed markets array
// @param markets_array_len_ - Length of the markets array
// @param current_collateral_id_ - Current collateral_id
// @returns positions_array_len - Length of the positions array
// @returns positions_array - Array with the positions
func populate_positions{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    positions_array_len_: felt,
    positions_array_: PositionDetailsWithMarket*,
    markets_iterator_: felt,
    markets_array_len_: felt,
    current_collateral_id_: felt,
) -> (positions_array_len: felt, positions_array: PositionDetailsWithMarket*) {
    alloc_locals;

    // If reached the end of the array, then return
    if (markets_array_len_ == markets_iterator_) {
        return (positions_array_len_, positions_array_);
    }

    // Get the market id at that position
    let (curr_market_id: felt) = collateral_to_market_array.read(
        collateral_id=current_collateral_id_, index=markets_iterator_
    );

    // Get Long position
    let (long_position: PositionDetails) = position_mapping.read(
        market_id=curr_market_id, direction=LONG
    );

    // Get Short position
    let (short_position: PositionDetails) = position_mapping.read(
        market_id=curr_market_id, direction=SHORT
    );

    // Get asset token decimal
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );
    let (market: Market) = IMarkets.get_market(
        contract_address=market_address, market_id_=curr_market_id
    );
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset: Asset) = IAsset.get_asset(contract_address=asset_address, id=market.asset);

    local is_long;
    local is_short;

    let (is_long_zero) = Math64x61_is_equal(long_position.position_size, 0, asset.token_decimal);
    if (is_long_zero == TRUE) {
        assert is_long = 0;
    } else {
        // Store it in the array
        let curr_position = PositionDetailsWithMarket(
            market_id=curr_market_id,
            direction=LONG,
            avg_execution_price=long_position.avg_execution_price,
            position_size=long_position.position_size,
            margin_amount=long_position.margin_amount,
            borrowed_amount=long_position.borrowed_amount,
            leverage=long_position.leverage,
            created_timestamp=long_position.created_timestamp,
            modified_timestamp=long_position.modified_timestamp,
            realized_pnl=long_position.realized_pnl,
        );
        assert positions_array_[positions_array_len_] = curr_position;
        assert is_long = 1;
    }

    let (is_short_zero) = Math64x61_is_equal(short_position.position_size, 0, asset.token_decimal);
    if (is_short_zero == TRUE) {
        assert is_short = 0;
    } else {
        // Store it in the array
        let curr_position = PositionDetailsWithMarket(
            market_id=curr_market_id,
            direction=SHORT,
            avg_execution_price=short_position.avg_execution_price,
            position_size=short_position.position_size,
            margin_amount=short_position.margin_amount,
            borrowed_amount=short_position.borrowed_amount,
            leverage=short_position.leverage,
            created_timestamp=short_position.created_timestamp,
            modified_timestamp=short_position.modified_timestamp,
            realized_pnl=short_position.realized_pnl,
        );
        assert positions_array_[positions_array_len_ + is_long] = curr_position;
        assert is_short = 1;
    }

    return populate_positions(
        positions_array_len_=positions_array_len_ + is_long + is_short,
        positions_array_=positions_array_,
        markets_iterator_=markets_iterator_ + 1,
        markets_array_len_=markets_array_len_,
        current_collateral_id_=current_collateral_id_,
    );
}

// @notice Internal Function to populate positions for ABR Payments
// @param positions_array_len_ - Length of the array
// @param positions_array_ - Required array of positions
// @param iterator_ - Current length of traversed array
// @param markets_array_len_ - Length of the markets array
// @param current_collateral_id_ - current collateral id of the positions being populated
// @param timestamp_filter_ - Timestamp by which to filter out the positions
// @returns positions_array_len - Length of the positions array
// @returns positions_array - Array with the positions
func populate_simplified_positions{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    positions_array_len_: felt,
    positions_array_: SimplifiedPosition*,
    markets_iterator_: felt,
    markets_array_len_: felt,
    current_collateral_id_: felt,
    timestamp_filter_: felt,
) -> (positions_array_len: felt, positions_array: SimplifiedPosition*) {
    alloc_locals;
    // If reached the end of the array, then return
    if (markets_iterator_ == markets_array_len_) {
        return (positions_array_len_, positions_array_);
    }

    // Get the market id at that position
    let (curr_market_id: felt) = collateral_to_market_array.read(
        collateral_id=current_collateral_id_, index=markets_iterator_
    );

    // Get Long position
    let (long_position: PositionDetails) = position_mapping.read(
        market_id=curr_market_id, direction=LONG
    );

    // Get Short position
    let (short_position: PositionDetails) = position_mapping.read(
        market_id=curr_market_id, direction=SHORT
    );

    // Get asset token decimal
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    );
    let (market: Market) = IMarkets.get_market(
        contract_address=market_address, market_id_=curr_market_id
    );
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    );
    let (asset: Asset) = IAsset.get_asset(contract_address=asset_address, id=market.asset);

    local is_long;
    local is_short;

    let within_timestamp_long = is_le(long_position.created_timestamp, timestamp_filter_);
    let (is_long_zero) = Math64x61_is_equal(long_position.position_size, 0, asset.token_decimal);

    let within_timestamp_short = is_le(short_position.created_timestamp, timestamp_filter_);
    let (is_short_zero) = Math64x61_is_equal(short_position.position_size, 0, asset.token_decimal);

    if (within_timestamp_long == TRUE) {
        if (is_long_zero == FALSE) {
            // Create the struct with the details
            let position_struct_long: SimplifiedPosition = SimplifiedPosition(
                market_id=curr_market_id, direction=LONG, position_size=long_position.position_size
            );
            assert positions_array_[positions_array_len_] = position_struct_long;
            assert is_long = 1;
        } else {
            assert is_long = 0;
        }
    } else {
        assert is_long = 0;
    }

    if (within_timestamp_short == TRUE) {
        if (is_short_zero == FALSE) {
            // Create the struct with the details
            let position_struct_short: SimplifiedPosition = SimplifiedPosition(
                market_id=curr_market_id,
                direction=SHORT,
                position_size=short_position.position_size,
            );
            assert positions_array_[positions_array_len_ + is_long] = position_struct_short;
            assert is_short = 1;
        } else {
            assert is_short = 0;
        }
    } else {
        assert is_short = 0;
    }

    // Recursively call the next market_id
    return populate_simplified_positions(
        positions_array_len_=positions_array_len_ + is_long + is_short,
        positions_array_=positions_array_,
        markets_iterator_=markets_iterator_ + 1,
        markets_array_len_=markets_array_len_,
        current_collateral_id_=current_collateral_id_,
        timestamp_filter_=timestamp_filter_,
    );
}

// @notice Internal function to fetch all collaterals and recurse over them to populate the positions for ABR
// @param positions_array_len_ - Length of the array
// @param positions_array_ - Required array of net positions
// @param collateral_array_iterator_ - Iterator to the collateral array
// @param collateral_array_len_ - Length of the collateral array
// @param timestamp_filter_ - Timestamp by which to filter the array
// @returns positions_array_len - Length of the net positions array
// @returns positions_array - Array with the net positions
func populate_simplified_positions_collaterals_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    positions_array_len_: felt,
    positions_array_: SimplifiedPosition*,
    collateral_array_iterator_: felt,
    collateral_array_len_: felt,
    timestamp_filter_: felt,
) -> (positions_array_len: felt, positions_array: SimplifiedPosition*) {
    alloc_locals;
    // If reached the end of the array, then return
    if (collateral_array_iterator_ == collateral_array_len_) {
        return (positions_array_len_, positions_array_);
    }

    // Get the market id at that position
    let (current_collateral_id: felt) = collateral_array.read(index=collateral_array_iterator_);

    // Get current collateral array length
    let (current_markets_array_len: felt) = collateral_to_market_array_len.read(
        collateral_id=current_collateral_id
    );

    // Recursively call the next market_id
    let (
        positions_array_len: felt, positions_array: SimplifiedPosition*
    ) = populate_simplified_positions(
        positions_array_len_=positions_array_len_,
        positions_array_=positions_array_,
        markets_iterator_=0,
        markets_array_len_=current_markets_array_len,
        current_collateral_id_=current_collateral_id,
        timestamp_filter_=timestamp_filter_,
    );

    return populate_simplified_positions_collaterals_recurse(
        positions_array_len_=positions_array_len,
        positions_array_=positions_array,
        collateral_array_iterator_=collateral_array_iterator_ + 1,
        collateral_array_len_=collateral_array_len_,
        timestamp_filter_=timestamp_filter_,
    );
}

// @notice Internal function to fetch all collaterals and recurse over them to populate the positions
// @param positions_array_len_ - Length of the array
// @param positions_array_ - Required array of net positions
// @param collateral_array_iterator_ - Iterator to the collateral array
// @param collateral_array_len_ - Length of the collateral array
// @returns positions_array_len - Length of the net positions array
// @returns positions_array - Array with the net positions
func populate_positions_collaterals_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    positions_array_len_: felt,
    positions_array_: PositionDetailsWithMarket*,
    collateral_array_iterator_: felt,
    collateral_array_len_: felt,
) -> (positions_array_len: felt, positions_array: PositionDetailsWithMarket*) {
    alloc_locals;
    // If reached the end of the array, then return
    if (collateral_array_iterator_ == collateral_array_len_) {
        return (positions_array_len_, positions_array_);
    }

    // Get the market id at that position
    let (current_collateral_id: felt) = collateral_array.read(index=collateral_array_iterator_);

    // Get current collateral array length
    let (current_markets_array_len: felt) = collateral_to_market_array_len.read(
        collateral_id=current_collateral_id
    );

    // Recursively call the next market_id
    let (
        positions_array_len: felt, positions_array: PositionDetailsWithMarket*
    ) = populate_positions(
        positions_array_len_=positions_array_len_,
        positions_array_=positions_array_,
        markets_iterator_=0,
        markets_array_len_=current_markets_array_len,
        current_collateral_id_=current_collateral_id,
    );

    return populate_positions_collaterals_recurse(
        positions_array_len_=positions_array_len,
        positions_array_=positions_array,
        collateral_array_iterator_=collateral_array_iterator_ + 1,
        collateral_array_len_=collateral_array_len_,
    );
}

// @notice Internal function to hash the order parameters
// @param orderRequest - Struct of order request to hash
// @param res - Hash of the details
func hash_order{pedersen_ptr: HashBuiltin*}(orderRequest: OrderRequest*) -> (res: felt) {
    let hash_ptr = pedersen_ptr;
    with hash_ptr {
        let (hash_state_ptr) = hash_init();
        let (hash_state_ptr) = hash_update(hash_state_ptr, orderRequest, 11);
        let (res) = hash_finalize(hash_state_ptr);
        let pedersen_ptr = hash_ptr;
        return (res=res);
    }
}

// @notice Internal function to check for hash collisions
// @param order_id - Order ID of the request
// @param order_hash - Hash of the corresponding order
func order_hash_check{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    order_id: felt, order_hash: felt
) {
    // Get the hash of the order associated with the order_id
    let (existing_hash) = order_id_mapping.read(order_id=order_id);
    // If the hash isn't stored in the contract yet
    if (existing_hash == 0) {
        order_id_mapping.write(order_id=order_id, value=order_hash);
        return ();
    }

    with_attr error_message("AccountManager: Hash mismatch") {
        assert existing_hash = order_hash;
    }
    return ();
}

// @notice Internal function to hash the withdrawal request parameters
// @param withdrawal_request_ - Struct of withdrawal Request to hash
// @param res - Hash of the details
func hash_withdrawal_request{pedersen_ptr: HashBuiltin*}(
    withdrawal_request_: WithdrawalRequestForHashing*
) -> (res: felt) {
    let hash_ptr = pedersen_ptr;
    with hash_ptr {
        let (hash_state_ptr) = hash_init();
        let (hash_state_ptr) = hash_update(hash_state_ptr, withdrawal_request_, 3);
        let (res) = hash_finalize(hash_state_ptr);
        let pedersen_ptr = hash_ptr;
        return (res=res);
    }
}

// @notice Internal function to add a market to the array
// @param market_id - Id of the market to tbe added
// @return 1 - If successfully added
func add_to_market_array{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, collateral_id_: felt
) {
    let (is_exists) = market_is_exist.read(market_id=market_id_);

    if (is_exists == TRUE) {
        return ();
    }

    let (arr_len) = collateral_to_market_array_len.read(collateral_id=collateral_id_);
    collateral_to_market_array.write(collateral_id=collateral_id_, index=arr_len, value=market_id_);

    market_to_index_mapping.write(market_id=market_id_, value=arr_len);
    collateral_to_market_array_len.write(collateral_id=collateral_id_, value=arr_len + 1);
    market_is_exist.write(market_id=market_id_, value=TRUE);
    return ();
}

// @notice Internal function called to remove a market_id when both positions are fully closed
// @param market_id - Id of the market
// @param collateral_id_ - collateral id
// @return 1 - If successfully removed
func remove_from_market_array{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    market_id_: felt, collateral_id_: felt
) {
    alloc_locals;

    let (index) = market_to_index_mapping.read(market_id=market_id_);
    let (arr_len) = collateral_to_market_array_len.read(collateral_id=collateral_id_);

    if (arr_len == 1) {
        collateral_to_market_array.write(collateral_id=collateral_id_, index=index, value=0);
    } else {
        let (last_id) = collateral_to_market_array.read(
            collateral_id=collateral_id_, index=arr_len - 1
        );
        collateral_to_market_array.write(collateral_id=collateral_id_, index=index, value=last_id);
        collateral_to_market_array.write(collateral_id=collateral_id_, index=arr_len - 1, value=0);
        market_to_index_mapping.write(market_id=last_id, value=index);
    }

    market_to_index_mapping.write(market_id=market_id_, value=0);
    market_is_exist.write(market_id=market_id_, value=FALSE);
    collateral_to_market_array_len.write(collateral_id=collateral_id_, value=arr_len - 1);
    return ();
}

// @notice Internal function to add collateral to the array
// @param new_asset_id - asset Id to be added
// @param iterator - index at which an asset to be added
// @param length - length of collateral array
func add_collateral{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    new_asset_id: felt, iterator: felt, length: felt
) {
    alloc_locals;
    if (iterator == length) {
        collateral_array.write(index=iterator, value=new_asset_id);
        collateral_array_len.write(iterator + 1);
        return ();
    }

    let (collateral_id) = collateral_array.read(index=iterator);
    local difference = collateral_id - new_asset_id;
    if (difference == 0) {
        return ();
    }

    return add_collateral(new_asset_id=new_asset_id, iterator=iterator + 1, length=length);
}

// @notice Internal function to recursively find the index of the withdrawal history to be updated
// @param request_id_ - Id of the withdrawal request
// @param arr_len_ - current index which is being checked to be updated
// @return index - returns the index which needs to be updated
func find_index_to_be_updated_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(request_id_: felt, arr_len_: felt) -> (index: felt) {
    if (arr_len_ == 0) {
        return (-1,);
    }

    let (request: WithdrawalHistory) = withdrawal_history_array.read(index=arr_len_ - 1);
    if (request.request_id == request_id_) {
        return (arr_len_ - 1,);
    }

    return find_index_to_be_updated_recurse(request_id_, arr_len_ - 1);
}

// @notice Internal function to recursively check for withdrawal replays
// @param request_id_ - Id of the withdrawal request
// @param arr_len_ - current index which is being checked to be updated
// @return - -1 if same withdrawal request already exists, else 1
func check_for_withdrawal_replay{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    request_id_: felt, arr_len_: felt
) -> (index: felt) {
    if (arr_len_ == 0) {
        return (1,);
    }

    let (request: WithdrawalHistory) = withdrawal_history_array.read(index=arr_len_ - 1);
    if (request.request_id == request_id_) {
        return (-1,);
    }

    return check_for_withdrawal_replay(request_id_, arr_len_ - 1);
}
