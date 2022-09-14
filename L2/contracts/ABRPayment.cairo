%lang starknet
%builtins pedersen range_check ecdsa

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math import abs_value, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.syscalls import get_block_timestamp
from contracts.Math_64x61 import Math64x61_mul
from contracts.Constants import (
    ABR_FUNDS_INDEX,
    ABR_INDEX,
    AccountRegistry_INDEX,
    Market_INDEX,
    SHORT,
)

from contracts.DataTypes import NetPositions
from contracts.interfaces.IABR import IABR
from contracts.interfaces.IABRFund import IABRFund
from contracts.interfaces.IAccountManager import IAccountManager
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IMarkets import IMarkets

##########
# Events #
##########

# Event emitted when abr payment called for a position
@event
func abr_payment_called_user_position(market_id : felt, account_address : felt, timestamp : felt):
end

###########
# Storage #
###########
# Stores the authregistry address
@storage_var
func registry_address() -> (contract_address : felt):
end
# Stores tbe contract version
@storage_var
func contract_version() -> (version : felt):
end

###############
# Constructor #
###############
# @notice
# @param registry_address_ - Address of the auth registry
# @param contract_version_ Version of the contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt, contract_version_ : felt
):
    with_attr error_message("Registry address and version cannot be 0"):
        assert_not_zero(contract_version_)
        assert_not_zero(registry_address_)
    end
    registry_address.write(registry_address_)
    contract_version.write(contract_version_)
    return ()
end

######################
# External Functions #
######################
# @notice Function to be called by the node
# @param account_addresses_len_ - Length of the account_addresses array being passed
# @param account_addresses_ - Account addresses array
@external
func pay_abr{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    account_addresses_len : felt, account_addresses : felt*
):
    # ## Signature checks go here ####
    # Get the account registry smart-contract
    let (registry) = registry_address.read()
    let (version) = contract_version.read()
    let (account_registry) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AccountRegistry_INDEX, version=version
    )
    # Get the market smart-contract
    let (market_contract) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    )
    # Get the ABR smart-contract
    let (abr_contract) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_INDEX, version=version
    )
    # Get the ABR-funding smart-contract
    let (abr_funding_contract) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=ABR_FUNDS_INDEX, version=version
    )
    return pay_abr_users(
        account_addresses_len,
        account_addresses,
        account_registry,
        market_contract,
        abr_contract,
        abr_funding_contract,
    )
end

######################
# Internal Functions #
######################
# @notice Internal function called by pay_abr_users_positions to transfer funds between ABR Fund and users
# @param account_address_ - Address of the user of whom the positions are passed
# @param abr_funding_ - Address of the ABR Fund contract
# @param collateral_id_ - Collateral id of the position
# @param market_id_ - Market id of the position
# @param abs_payment_amount_ - Absolute value of ABR payment
func user_pays{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    account_address_ : felt,
    abr_funding_ : felt,
    collateral_id_ : felt,
    market_id_ : felt,
    abs_payment_amount_ : felt,
):
    IAccountManager.transfer_from_abr(
        contract_address=account_address_,
        collateral_id_=collateral_id_,
        market_id_=market_id_,
        amount_=abs_payment_amount_,
    )
    IABRFund.deposit(
        contract_address=abr_funding_,
        account_address_=account_address_,
        market_id_=market_id_,
        amount_=abs_payment_amount_,
    )
    return ()
end

# @notice Internal function called by pay_abr_users_positions to transfer funds between ABR Fund and users
# @param account_address_ - Address of the user of whom the positions are passed
# @param abr_funding_ - Address of the ABR Fund contract
# @param collateral_id_ - Collateral id of the position
# @param market_id_ - Market id of the position
# @param abs_payment_amount_ - Absolute value of ABR payment
func user_receives{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    account_address_ : felt,
    abr_funding_ : felt,
    collateral_id_ : felt,
    market_id_ : felt,
    abs_payment_amount_ : felt,
):
    IABRFund.withdraw(
        contract_address=abr_funding_,
        account_address_=account_address_,
        market_id_=market_id_,
        amount_=abs_payment_amount_,
    )
    IAccountManager.transfer_abr(
        contract_address=account_address_,
        collateral_id_=collateral_id_,
        market_id_=market_id_,
        amount_=abs_payment_amount_,
    )
    return ()
end

# @notice Internal function called by pay_abr_users to iterate throught the positions of the account
# @param account_address - Address of the user of whom the positions are passed
# @param net_positions_len_ - Length of the net positions array of the user
# @param net_positions_ - Net Positions array of the user
# @param market_contract_ - Address of the Market contract
# @param abr_contract_ - Address of the ABR contract
# @param abr_funding_contract_ - Address of the ABR Funding contract
func pay_abr_users_positions{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    account_address_ : felt,
    net_positions_len_ : felt,
    net_positions_ : NetPositions*,
    market_contract_ : felt,
    abr_contract_ : felt,
    abr_funding_ : felt,
):
    alloc_locals

    if net_positions_len_ == 0:
        return ()
    end

    # Check if abr already collected
    let (is_called) = IAccountManager.timestamp_check(
        contract_address=account_address_, market_id_=[net_positions_].market_id
    )

    # Get the collateral ID of the market
    let (collateral_id) = IMarkets.get_collateral_from_market(
        contract_address=market_contract_, market_id=[net_positions_].market_id
    )

    if is_called == 1:
        return pay_abr_users_positions(
            account_address_,
            net_positions_len_ - 1,
            net_positions_ + NetPositions.SIZE,
            market_contract_,
            abr_contract_,
            abr_funding_,
        )
    end

    # Get the abr value
    let (abr : felt, price : felt, timestamp : felt) = IABR.get_abr_value(
        contract_address=abr_contract_, market_id=[net_positions_].market_id
    )

    # Find if the abr_rate is +ve or -ve
    let (position_value) = Math64x61_mul(price, [net_positions_].position_size)
    let (payment_amount) = Math64x61_mul(abr, position_value)
    let (abs_payment_amount) = abs_value(payment_amount)
    let (is_negative) = is_le(abr, 0)
    let (is_negative_net_size) = is_le([net_positions_].position_size, 0)

    # If the abr is negative
    if is_negative == TRUE:
        if is_negative_net_size == 1:
            # user pays
            user_pays(
                account_address_,
                abr_funding_,
                collateral_id,
                [net_positions_].market_id,
                abs_payment_amount,
            )
        else:
            # user receives
            user_receives(
                account_address_,
                abr_funding_,
                collateral_id,
                [net_positions_].market_id,
                abs_payment_amount,
            )
        end
        # If the abr is positive
    else:
        if is_negative_net_size == 1:
            # user receives
            user_receives(
                account_address_,
                abr_funding_,
                collateral_id,
                [net_positions_].market_id,
                abs_payment_amount,
            )
        else:
            # user pays
            user_pays(
                account_address_,
                abr_funding_,
                collateral_id,
                [net_positions_].market_id,
                abs_payment_amount,
            )
        end
    end

    # Get the latest block
    let (block_timestamp) = get_block_timestamp()

    abr_payment_called_user_position.emit(
        market_id=[net_positions_].market_id,
        account_address=account_address_,
        timestamp=block_timestamp,
    )
    return pay_abr_users_positions(
        account_address_,
        net_positions_len_ - 1,
        net_positions_ + NetPositions.SIZE,
        market_contract_,
        abr_contract_,
        abr_funding_,
    )
end

# @notice Internal function called by pay_abr to iterate throught the account_addresses array
# @param account_addresses_len_ - Length of thee account_addresses array being passed
# @param account_addresses_ - Account addresses array
# @param account_registry_ - Address of the Account Registry contract
# @param market_contract_ - Address of the Market contract
# @param abr_contract_ - Address of the ABR contract
# @param abr_funding_contract_ - Address of the ABR Funding contract
func pay_abr_users{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    account_addresses_len_ : felt,
    account_addresses_ : felt*,
    account_registry_ : felt,
    market_contract_ : felt,
    abr_contract_ : felt,
    abr_funding_contract_ : felt,
):
    if account_addresses_len_ == 0:
        return ()
    end

    # Check if the user is added to Account Registry
    let (is_registered_user) = IAccountRegistry.is_registered_user(
        contract_address=account_registry_, address_=[account_addresses_]
    )

    # If not, skip the current iteration
    if is_registered_user == FALSE:
        return pay_abr_users(
            account_addresses_len_ - 1,
            account_addresses_ + 1,
            account_registry_,
            market_contract_,
            abr_contract_,
            abr_funding_contract_,
        )
    end

    # Get all the open positions of the user
    let (
        net_positions_len : felt, net_positions : NetPositions*
    ) = IAccountManager.get_net_positions(contract_address=[account_addresses_])

    # Do abr payments for each position
    pay_abr_users_positions(
        [account_addresses_],
        net_positions_len,
        net_positions,
        market_contract_,
        abr_contract_,
        abr_funding_contract_,
    )

    return pay_abr_users(
        account_addresses_len_ - 1,
        account_addresses_ + 1,
        account_registry_,
        market_contract_,
        abr_contract_,
        abr_funding_contract_,
    )
end
