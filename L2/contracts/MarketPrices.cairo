%lang starknet
%builtins pedersen range_check ecdsa

from contracts.DataTypes import MarketPrice, Market
from contracts.interfaces.IMarkets import IMarkets
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IAdminAuth import IAdminAuth
from contracts.Constants import Trading_INDEX, Market_INDEX, AdminAuth_INDEX, ManageMarkets_ACTION
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address, get_block_timestamp
from starkware.cairo.common.math import assert_not_zero

#
# Storage
#

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of AuthorizedRegistry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

# @notice Mapping between market ID and Market Prices
@storage_var
func market_prices(id : felt) -> (res : MarketPrice):
end

#
# Constructor
#

# @notice Constructor for the smart-contract
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

#
# Getters
#

# @notice function to get market price
# @param market_id_ - Id of the market pair
@external
func get_market_price{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt,
)-> (market_price : MarketPrice):
    let (res) = market_prices.read(id=market_id_)
    return (market_price=res)
end

#
# Business logic
#

# @notice function to update market price
# @param market_id_ - Id of the market
# @param price_ - price of the market pair
@external
func update_market_price{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    market_id_ : felt,
    price_ : felt
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
    let (market : Market) = IMarkets.getMarket(
        contract_address=market_contract_address,
        id=market_id_
    )

    # Create a struct object for the market prices
    tempvar new_market_price : MarketPrice = MarketPrice(
        asset_id=market.asset,
        collateral_id=market.assetCollateral,
        timestamp=timestamp_,
        price=price_,
    )
    
    market_prices.write(id=market_id_, value=new_market_price)
    return ()
end