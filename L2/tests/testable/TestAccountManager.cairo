%lang starknet

from starkware.cairo.common.bool import FALSE
from starkware.cairo.common.cairo_builtins import HashBuiltin

###########
# Storage #
###########

# Stores balance of an asset
@storage_var
func balance(assetID : felt) -> (res : felt):
end

# Stores all collaterals held by the user
@storage_var
func collateral_array(index : felt) -> (collateral_id : felt):
end

# Stores length of the collateral array
@storage_var
func collateral_array_len() -> (len : felt):
end


######################
# External Functions #
######################

@external
func set_balance{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetID_ : felt, amount_ : felt
):
    let (curr_balance) = balance.read(assetID=assetID_)
    balance.write(assetID=assetID_, value=amount_)
    let (array_len) = collateral_array_len.read()

    if curr_balance == 0:
        add_collateral(new_asset_id=assetID_, iterator=0, length=array_len)
        return()
    else:
        return()
    end
end

######################
# Internal Functions #
######################

func add_collateral{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    new_asset_id : felt, iterator : felt, length : felt
):
    alloc_locals
    if iterator == length:
        collateral_array.write(index=iterator, value=new_asset_id)
        collateral_array_len.write(iterator + 1)
        return ()
    end

    let (collateral_id) = collateral_array.read(index=iterator)
    local difference = collateral_id - new_asset_id
    if difference == 0:
        return ()
    end

    return add_collateral(new_asset_id=new_asset_id, iterator=iterator + 1, length=length)
end

