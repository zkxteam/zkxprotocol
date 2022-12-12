%lang starknet

from starkware.cairo.common.bool import FALSE
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address, get_contract_address
from starkware.cairo.common.uint256 import Uint256, uint256_eq, uint256_le, uint256_lt, uint256_sub

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

// @notice - This function is used for distributing reward tokens
@external
func distribute_reward_tokens{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    trader_address_: felt, reward_amount_Uint256_: Uint256, l1_token_address_: felt
) {
    alloc_locals;
    let (registry) = CommonLib.get_registry_address();
    let (version) = CommonLib.get_contract_version();

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

    let (native_token_l2_address: felt) = IStarkway.get_native_token_address(
        contract_address=starkway_contract_address, token_id=l1_token_address_
    );

    let (liquidity_pool_address) = get_contract_address();
    local reward_amount_Uint256: Uint256;
    if (native_token_l2_address != 0) {
        // Fetch current balance of the token
        let current_balance_Uint256: Uint256 = IERC20.balanceOf(
            native_token_l2_address, liquidity_pool_address
        );

        // if current balance can cover the reward amount then, we will transfer the reward and return
        // if current balance can cover the reward amount partially, then we will transfer the balance available and
        // goto the next whitelisted token
        let zero_Uint256: Uint256 = Uint256(0, 0);
        let (result) = uint256_lt(current_balance_Uint256, reward_amount_Uint256_);
        if (result == FALSE) {
            IERC20.transfer(native_token_l2_address, trader_address_, reward_amount_Uint256_);
            assert reward_amount_Uint256 = Uint256(0, 0);
            return ();
        } else {
            let (status) = uint256_eq(current_balance_Uint256, zero_Uint256);
            if (status == FALSE) {
                IERC20.transfer(native_token_l2_address, trader_address_, current_balance_Uint256);
                let (remaining_reward) = uint256_sub(
                    reward_amount_Uint256_, current_balance_Uint256
                );
                assert reward_amount_Uint256 = remaining_reward;
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            } else {
                assert reward_amount_Uint256 = reward_amount_Uint256_;
                tempvar syscall_ptr = syscall_ptr;
                tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
                tempvar range_check_ptr = range_check_ptr;
            }
        }
    } else {
        tempvar syscall_ptr = syscall_ptr;
        tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
        tempvar range_check_ptr = range_check_ptr;
    }

    let (
        token_address_list_len: felt, token_address_list: felt*
    ) = IStarkway.get_whitelisted_token_addresses(
        contract_address=starkway_contract_address, token_id=l1_token_address_
    );

    return transfer_tokens_recurse(
        trader_address_,
        reward_amount_Uint256,
        liquidity_pool_address,
        0,
        token_address_list_len,
        token_address_list,
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

    let (native_token_l2_address: felt) = IStarkway.get_native_token_address(
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

func transfer_tokens_recurse{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(
    trader_address_: felt,
    reward_amount_Uint256_: Uint256,
    liquidity_pool_address_: felt,
    iterator_: felt,
    token_address_list_len: felt,
    token_address_list: felt*,
) {
    alloc_locals;
    if (iterator_ == token_address_list_len) {
        return ();
    }

    // Fetch current balance of the token
    let current_balance_Uint256: Uint256 = IERC20.balanceOf(
        [token_address_list], liquidity_pool_address_
    );

    // if current balance can cover the reward amount then, we will transfer the reward and return
    // if current balance can cover the reward amount partially, then we will transfer the balance available and
    // goto the next whitelisted token
    local reward_amount_Uint256: Uint256;
    let zero_Uint256: Uint256 = Uint256(0, 0);
    let (result) = uint256_lt(current_balance_Uint256, reward_amount_Uint256_);
    if (result == FALSE) {
        IERC20.transfer([token_address_list], trader_address_, reward_amount_Uint256_);
        assert reward_amount_Uint256 = Uint256(0, 0);
        return ();
    } else {
        let (status) = uint256_eq(current_balance_Uint256, zero_Uint256);
        if (status == FALSE) {
            IERC20.transfer([token_address_list], trader_address_, current_balance_Uint256);
            let (remaining_reward) = uint256_sub(reward_amount_Uint256_, current_balance_Uint256);
            assert reward_amount_Uint256 = remaining_reward;
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        } else {
            assert reward_amount_Uint256 = reward_amount_Uint256_;
            tempvar syscall_ptr = syscall_ptr;
            tempvar pedersen_ptr: HashBuiltin* = pedersen_ptr;
            tempvar range_check_ptr = range_check_ptr;
        }
    }

    // Recursively transfer tokens
    return transfer_tokens_recurse(
        trader_address_,
        reward_amount_Uint256,
        liquidity_pool_address_,
        iterator_ + 1,
        token_address_list_len,
        token_address_list + 1,
    );
}
