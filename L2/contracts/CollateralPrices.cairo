%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_block_timestamp

from contracts.Constants import MasterAdmin_ACTION, ManageCollateralPrices_ACTION
from contracts.DataTypes import CollateralPrice
from contracts.libraries.Utils import verify_caller_authority

##########
# Events #
##########

# Event emitted whenever update_collateral_price() is called
@event
func update_collateral_price_called(collateral_id : felt, price : felt):
end

# this event is emitted whenever the version for this contract is changed by the admin
@event
func contract_version_changed(new_version: felt):
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
    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Auth check
    with_attr error_message("Caller is not authorized to update collateral prices"):
        verify_caller_authority(registry, version, ManageCollateralPrices_ACTION)
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

# @notice external function to set contract version
# @param new_version - new version of the contract
@external
func set_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    new_version : felt
):
    let (current_registry_address) = registry_address.read()
    let (current_version) = contract_version.read()

    verify_caller_authority(current_registry_address, current_version, MasterAdmin_ACTION)
    contract_version.write(new_version)
    contract_version_changed.emit(new_version=new_version)
    return ()
end
