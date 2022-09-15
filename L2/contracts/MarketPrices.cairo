%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_nn, assert_not_zero
from starkware.starknet.common.syscalls import get_block_timestamp, get_caller_address

from contracts.Constants import (
    AdminAuth_INDEX,
    ManageMarkets_ACTION,
    Market_INDEX,
    MasterAdmin_ACTION,
    Trading_INDEX,
)
from contracts.DataTypes import Market, MarketPrice
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IMarkets import IMarkets
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_assert64x61

##########
# Events #
##########

# Event emitted whenever update_market_price() is called
@event
func update_market_price_called(market_id : felt, price : felt):
end

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

# Mapping between market ID and Market Prices
@storage_var
func market_prices(id : felt) -> (res : MarketPrice):
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

# @notice function to get market price
# @param market_id_ - Id of the market pair
@view
func get_market_price{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt
) -> (market_price : MarketPrice):
    let (res) = market_prices.read(id=market_id_)
    return (market_price=res)
end

######################
# External Functions #
######################

# @notice function to update market price
# @param market_id_ - Id of the market
# @param price_ - price of the market pair
@external
func update_market_price{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt, price_ : felt
):
    let (caller) = get_caller_address()
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    let (auth_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=AdminAuth_INDEX, version=version
    )

    # Auth Check
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_address, address=caller, action=ManageMarkets_ACTION
    )

    if access == 0:
        # Get trading contract address
        let (trading_contract_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=Trading_INDEX, version=version
        )

        with_attr error_message("Caller is not authorized to update market price"):
            assert caller = trading_contract_address
        end

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end

    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Calculate the timestamp
    let (timestamp_) = get_block_timestamp()

    # Get market contract address
    let (market_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    )

    # Get Market from the corresponding Id
    let (market : Market) = IMarkets.get_market(
        contract_address=market_contract_address, id=market_id_
    )

    with_attr error_message("Price cannot be negative"):
        assert_nn(price_)
    end

    with_attr error_message("Price should be within 64x61 range"):
        Math64x61_assert64x61(price_)
    end

    with_attr error_message("Market does not exist"):
        assert_not_zero(market.asset)
    end

    # Create a struct object for the market prices
    tempvar new_market_price : MarketPrice = MarketPrice(
        asset_id=market.asset,
        collateral_id=market.assetCollateral,
        timestamp=timestamp_,
        price=price_,
        )

    market_prices.write(id=market_id_, value=new_market_price)

    # update_market_price_called event is emitted
    update_market_price_called.emit(market_id=market_id_, price=price_)

    return ()
end
