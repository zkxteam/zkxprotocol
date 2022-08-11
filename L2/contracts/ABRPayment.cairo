%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math import abs_value, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from contracts.Math_64x61 import (
    Math64x61_mul
)
from contracts.Constants import ABR_FUNDS_INDEX, ABR_INDEX, AccountRegistry_INDEX, Market_INDEX, SHORT
from contracts.DataTypes import OrderDetailsWithIDs
from contracts.interfaces.IABR import IABR
from contracts.interfaces.IABRFund import IABRFund
from contracts.interfaces.IAccount import IAccount
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IMarkets import IMarkets

###########
# Storage #
###########

@storage_var
func registry_address() -> (contract_address : felt):
end

@storage_var
func contract_version() -> (version : felt):
end

###############
# Constructor #
###############

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
# @param account_addresses_len - Length of thee account_addresses array being passed
# @param account_addresses - Account addresses array
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
# @param account_address - Address of the user of whom the positions are passed
# @param abr_funding - Address of the ABR Fund contract
# @param collateral_id - Collateral id of the position
# @param market_id - Market id of the position
# @param abs_payment_amount - Absolute value of ABR payment 
func user_pays{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    account_address : felt, abr_funding : felt, collateral_id : felt, market_id : felt, abs_payment_amount : felt
):
    IAccount.transfer_from_abr(
        contract_address=account_address,
        assetID_=collateral_id,
        marketID_=market_id,
        amount=abs_payment_amount,
    )
    IABRFund.deposit(
        contract_address=abr_funding, market_id_=market_id, amount=abs_payment_amount
    )

    return()
end

# @notice Internal function called by pay_abr_users_positions to transfer funds between ABR Fund and users
# @param account_address - Address of the user of whom the positions are passed
# @param abr_funding - Address of the ABR Fund contract
# @param collateral_id - Collateral id of the position
# @param market_id - Market id of the position
# @param abs_payment_amount - Absolute value of ABR payment 
func user_receives{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    account_address : felt, abr_funding : felt, collateral_id : felt, market_id : felt, abs_payment_amount : felt
):
    IABRFund.withdraw(
        contract_address=abr_funding, market_id_=market_id, amount=abs_payment_amount
    )

    IAccount.transfer_abr(
        contract_address=account_address,
        assetID_=collateral_id,
        marketID_=market_id,
        amount=abs_payment_amount,
    )

    return()
end



# @notice Internal function called by pay_abr_users to iterate throught the positions of the account
# @param account_address - Address of the user of whom the positions are passed
# @param positions_len - Length of the positions array of the user
# @param positions - Positions array of the user
# @param market_contract - Address of the Market contract
# @param abr_contract - Address of the ABR contract
# @param abr_funding_contract - Address of the ABR Funding contract
func pay_abr_users_positions{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    account_address : felt,
    positions_len : felt,
    positions : OrderDetailsWithIDs*,
    market_contract : felt,
    abr_contract : felt,
    abr_funding : felt,
):
    alloc_locals

    if positions_len == 0:
        return ()
    end

    # Get the market id from market contract
    let (market_id) = IMarkets.getMarket_from_assets(
        contract_address=market_contract,
        asset_id=[positions].assetID,
        collateral_id=[positions].collateralID,
    )

    # Check if abr already collected
    let (is_called) = IAccount.timestamp_check(
        contract_address=account_address, market_id=market_id
    )

    if is_called == 1:
        return pay_abr_users_positions(
            account_address,
            positions_len - 1,
            positions + OrderDetailsWithIDs.SIZE,
            market_contract,
            abr_contract,
            abr_funding,
        )
    end

    # Get the abr value
    let (abr : felt, price : felt, timestamp : felt) = IABR.get_abr_value(
        contract_address=abr_contract, market_id=market_id
    )

    # Find if the abr_rate is +ve or -ve
    let (position_value) = Math64x61_mul(price, [positions].portionExecuted)
    let (payment_amount) = Math64x61_mul(abr, position_value)
    let (abs_payment_amount) = abs_value(payment_amount)
    let (is_negative) = is_le(abr, 0)

    # If the abr is negative
    if is_negative == 1:
        if [positions].direction == SHORT:
            # user pays
            user_pays(account_address, abr_funding, [positions].collateralID, market_id, abs_payment_amount)
        else:
            # user receives
            user_receives(account_address, abr_funding, [positions].collateralID, market_id, abs_payment_amount)
        end
    # If the abr is positive
    else:
        if [positions].direction == SHORT:
            # user receives
            user_receives(account_address, abr_funding, [positions].collateralID, market_id, abs_payment_amount)
        else:
            # user pays
            user_pays(account_address, abr_funding, [positions].collateralID, market_id, abs_payment_amount)
        end
    end

    return pay_abr_users_positions(
        account_address,
        positions_len - 1,
        positions + OrderDetailsWithIDs.SIZE,
        market_contract,
        abr_contract,
        abr_funding,
    )
end

# @notice Internal function called by pay_abr to iterate throught the account_addresses array
# @param account_addresses_len - Length of thee account_addresses array being passed
# @param account_addresses - Account addresses array
# @param account_registry - Address of the Account Registry contract
# @param market_contract - Address of the Market contract
# @param abr_contract - Address of the ABR contract
# @param abr_funding_contract - Address of the ABR Funding contract
func pay_abr_users{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    account_addresses_len : felt,
    account_addresses : felt*,
    account_registry : felt,
    market_contract : felt,
    abr_contract : felt,
    abr_funding_contract : felt,
):
    if account_addresses_len == 0:
        return ()
    end

    # Check if the user is added to Account Registry
    let (is_registered_user) = IAccountRegistry.is_registered_user(
        contract_address=account_registry, address_=[account_addresses]
    )

    # If not, skip the current iteration
    if is_registered_user == 0:
        return pay_abr_users(
            account_addresses_len - 1,
            account_addresses + 1,
            account_registry,
            market_contract,
            abr_contract,
            abr_funding_contract,
        )
    end

    # Get all the open positions of the user
    let (positions_len : felt, positions : OrderDetailsWithIDs*) = IAccount.return_array_positions(
        contract_address=[account_addresses]
    )

    # Do abr payments for each position
    pay_abr_users_positions(
        [account_addresses],
        positions_len,
        positions,
        market_contract,
        abr_contract,
        abr_funding_contract,
    )

    return pay_abr_users(
        account_addresses_len - 1,
        account_addresses + 1,
        account_registry,
        market_contract,
        abr_contract,
        abr_funding_contract,
    )
end

