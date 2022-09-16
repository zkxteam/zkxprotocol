%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_nn, assert_not_zero
from starkware.starknet.common.syscalls import get_block_timestamp

from contracts.Constants import Asset_INDEX, MasterAdmin_ACTION, ManageCollateralPrices_ACTION
from contracts.DataTypes import Asset, CollateralPrice
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.libraries.CommonStorageLibrary import CommonLib
from contracts.libraries.Utils import verify_caller_authority
from contracts.Math_64x61 import Math64x61_assert64x61

##########
# Events #
##########

# Event emitted whenever update_collateral_price() is called
@event
func update_collateral_price_called(collateral_id : felt, price : felt):
end

# this event is emitted whenever the version for this contract is changed by the admin
@event
func contract_version_changed(new_version : felt):
end

###########
# Storage #
###########

# Mapping between collateral ID and collateral Prices
@storage_var
func collateral_prices(id : felt) -> (res : CollateralPrice):
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
    CommonLib.initialize(registry_address_, version_)
    return ()
end

##################
# View Functions #
##################

# @notice function to get collateral price
# @param collateral_id_ - Id of the collateral
@view
func get_collateral_price{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    collateral_id_ : felt
) -> (collateral_price : CollateralPrice):
    let (res) = collateral_prices.read(id=collateral_id_)
    return (collateral_price=res)
end

######################
# External Functions #
######################

# @notice function to update collateral price
# @param collateral_id_ - Id of the collateral
# @param price_ - price of the collateral in USD
@external
func update_collateral_price{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    collateral_id_ : felt, price_ : felt
):
    let (registry) = CommonLib.get_registry_address()
    let (version) = CommonLib.get_contract_version()

    # Auth check
    with_attr error_message("Caller is not authorized to update collateral prices"):
        verify_caller_authority(registry, version, ManageCollateralPrices_ACTION)
    end

    with_attr error_message("Price cannot be negative"):
        assert_nn(price_)
    end

    with_attr error_message("Price should within 64x61 range"):
        Math64x61_assert64x61(price_)
    end

    # Get asset contract address
    let (asset_contract_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    )

    # Get Asset for the corresponding Id
    let (asset : Asset) = IAsset.get_asset(
        contract_address=asset_contract_address, id=collateral_id_
    )

    with_attr error_message("Asset does not exist"):
        assert_not_zero(asset.ticker)
    end

    # Calculate the timestamp
    let (timestamp_) = get_block_timestamp()

    # Create a struct object for the collateral prices
    tempvar new_collateral_price : CollateralPrice = CollateralPrice(
        timestamp=timestamp_,
        price_in_usd=price_,
        )

    collateral_prices.write(id=collateral_id_, value=new_collateral_price)

    # update_collateral_price_called event is emitted
    update_collateral_price_called.emit(collateral_id=collateral_id_, price=price_)

    return ()
end
