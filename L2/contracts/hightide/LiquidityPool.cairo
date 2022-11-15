%lang starknet

from starkware.cairo.common.bool import FALSE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address
from starkware.cairo.common.uint256 import Uint256, uint256_le

from contracts.Constants import Hightide_INDEX, Starkway_INDEX
from contracts.DataTypes import HighTideMetaData, RewardToken
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IERC20 import IERC20
from contracts.interfaces.IHighTide import IHighTide
from contracts.interfaces.IStarkway import IStarkway
from contracts.libraries.CommonLibrary import CommonLib

// ///////////
// Storage //
// ///////////

// Stores hightide id of the corresponding liquidity pool contract
@storage_var
func hightide_id() -> (id: felt) {
}

// ///////////////
// Constructor //
// ///////////////

// @notice Constructor of the smart-contract
// @param high_tide_id_ - id of hightide
// @param registry_address_ Address of the AuthorizedRegistry contract
// @param version_ Version of this contract
@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    high_tide_id_: felt, registry_address_: felt, version_: felt
) {
    with_attr error_message("LiquidityPool: Hightide id cannot be 0") {
        assert_not_zero(high_tide_id_);
    }

    hightide_id.write(high_tide_id_);
    CommonLib.initialize(registry_address_, version_);
    return ();
}

// ///////////
// External //
// ///////////

// @notice - This function is used for either returning or burning the tokens
@external
func perform_return_or_burn{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}() {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();
    let (id) = hightide_id.read();

    // Get Starkway contract address
    let (local starkway_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Starkway_INDEX, version=version
    );

    // Get Hightide contract address
    let (local hightide_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Hightide_INDEX, version=version
    );

    // Make sure this function is called from hightide contract
    let (caller) = get_caller_address();
    with_attr error_message("LiquidityPool: caller is not hightide contract") {
        assert caller = hightide_contract_address;
    }

    let (
        reward_tokens_list_len: felt, reward_tokens_list: RewardToken*
    ) = IHighTide.get_hightide_reward_tokens(
        contract_address=hightide_contract_address, hightide_id=id
    );

    let (hightide_metadata: HighTideMetaData) = IHighTide.get_hightide(
        contract_address=hightide_contract_address, hightide_id=id
    );

    return reward_tokens_recurse(
        hightide_metadata.token_lister_address,
        hightide_metadata.is_burnable,
        hightide_metadata.liquidity_pool_address,
        starkway_contract_address,
        0,
        reward_tokens_list_len,
        reward_tokens_list,
    );
}

// ///////////
// Internal //
// ///////////

func reward_tokens_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    token_lister_address_: felt,
    is_burnable_: felt,
    liquidity_pool_address_: felt,
    starkway_contract_address_: felt,
    iterator_: felt,
    reward_tokens_list_len: felt,
    reward_tokens_list: RewardToken*,
) {
    if (iterator_ == reward_tokens_list_len) {
        return ();
    }

    let (native_token_l2_address: felt) = IStarkway.get_native_token_l2_address(
        contract_address=starkway_contract_address_, token_id=[reward_tokens_list].token_id
    );

    if (native_token_l2_address != 0) {
        let current_balance_Uint256: Uint256 = IERC20.balanceOf(
            native_token_l2_address, liquidity_pool_address_
        );

        let zero_Uint256: Uint256 = cast((low=0, high=0), Uint256);
        let (result) = uint256_le(current_balance_Uint256, zero_Uint256);
        if (result == FALSE) {
            if (is_burnable_ == FALSE) {
                IERC20.transfer(
                    native_token_l2_address, token_lister_address_, current_balance_Uint256
                );
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            } else {
                IERC20.burn(native_token_l2_address, current_balance_Uint256);
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }
        } else {
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    let (
        contract_address_list_len: felt, contract_address_list: felt*
    ) = IStarkway.get_whitelisted_token_addresses(
        contract_address=starkway_contract_address_, token_id=[reward_tokens_list].token_id
    );

    transfer_or_burn_tokens_recurse(
        token_lister_address_,
        is_burnable_,
        liquidity_pool_address_,
        0,
        contract_address_list_len,
        contract_address_list,
    );

    return reward_tokens_recurse(
        token_lister_address_,
        is_burnable_,
        liquidity_pool_address_,
        starkway_contract_address_,
        iterator_ + 1,
        reward_tokens_list_len,
        reward_tokens_list + RewardToken.SIZE,
    );
}

func transfer_or_burn_tokens_recurse{
    syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr
}(
    token_lister_address_: felt,
    is_burnable_: felt,
    liquidity_pool_address_: felt,
    iterator_: felt,
    contract_address_list_len: felt,
    contract_address_list: felt*,
) {
    if (iterator_ == contract_address_list_len) {
        return ();
    }

    let current_balance_Uint256: Uint256 = IERC20.balanceOf(
        [contract_address_list], liquidity_pool_address_
    );

    let zero_Uint256: Uint256 = cast((low=0, high=0), Uint256);
    let (result) = uint256_le(current_balance_Uint256, zero_Uint256);
    if (result == FALSE) {
        if (is_burnable_ == FALSE) {
            IERC20.transfer(
                [contract_address_list], token_lister_address_, current_balance_Uint256
            );
        } else {
            // burn tokens by sending it to dead address
            IERC20.transfer([contract_address_list], 0x0000DEAD, current_balance_Uint256);
        }
        tempvar syscall_ptr = syscall_ptr;
    } else {
        tempvar syscall_ptr = syscall_ptr;
    }

    return transfer_or_burn_tokens_recurse(
        token_lister_address_,
        is_burnable_,
        liquidity_pool_address_,
        iterator_ + 1,
        contract_address_list_len,
        contract_address_list + 1,
    );
}
