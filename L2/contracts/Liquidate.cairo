%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.common.syscalls import get_contract_address
from starkware.cairo.common.math import assert_not_zero, assert_nn, assert_le, assert_in_range
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.hash_state import hash_init, hash_finalize, hash_update
from contracts.Math_64x61 import mul_fp, div_fp

struct Positions:
    member assetID : felt
    member collateralID : felt
    member price : felt
    member executionPrice : felt
    member positionSize : felt
    member orderType : felt
    member direction : felt
    member portionExecuted : felt
    member status : felt
end

struct PriceData:
    member assetID : felt
    member collateralID : felt
    member price : felt
end

func check_liquidation_recurse{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    current_position : Position,
    positions_len : felt,
    positions : Position*,
    prices_len : felt,
    prices : PriceData*,
    asset_value_total : felt,
    maintanence_req_total : felt,
) -> (res : felt):
    alloc_locals
    # Check if the list is empty, if yes return 1
    if positions_len == 0:
        let (is_liquidation) = is_le(maintanence_req_total, asset_value_total)
        return (is_liquidation)
    end

    # Create a struct object for the order
    tempvar position : Positions = Positions(
        assetID=[positions].assetID,
        collateralID=[positions].collateralID,
        price=[positions].price,
        executionPrice=[positions].executionPrice,
        positionSize=[positions].positionSize,
        orderType=[positions].orderType,
        direction=[positions].direction,
        portionExecuted=[positions].portionExecuted,
        status=[positions].status
        )

    tempvar asset_price : PriceData = PriceData(
        assetID=[prices].assetID,
        collateralID=[prices].collateralID,
        price=[prices].price
        )

    with_attr error_message("assetID and collateralID do not match"):
        assert position.assetID = asset_price.assetID
        assert position.collateralID = asset_price.collateralID
    end

    local asset_value = mul_fp(position.portionExecuted, asset_price.price)
    local margin_fraction = IAsset.get_maintanence_margin(contract_address=asset_address, id=position.assetId)

    local maintanence_req = margin_fraction * asset_price.price * position.portionExecuted

    return check_liquidation_recurse(
        current_position,
        positions_len - 1,
        positions + Positions.SIZE,
        prices_len - 1,
        prices + PriceData.SIZE,
        asset_value_total + asset_value,
        maintanence_req_total + maintanence_req,
    )
end

@external
func check_liquidation{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    public_address : felt, position_id : felt, prices_len : felt, prices : PriceData*
) -> (res : felt):
    alloc_locals
    let (positions_len : felt, positions : Positions*) = IAccount.return_array(
        contract_address=public_address
    )

    with_attr error_message("Position array length is 0"):
        assert_not_zero(positions_len)
    end

    let (current_position : Positions) = IAccount.get_order_data(
        contract_address=public_address, orderID_=position_id
    )

    with_attr error_message("The position given doesn't exist"):
        assert_not_zero(current_position.assetID)
    end

    with_attr error_message("No of positions doesn't match no of prices"):
        assert positions_len = prices_len
    end

    let (liq_result) = check_liquidation_recurse(
        current_position, positions_len, positions, prices_len, prices, 0, 0
    )

    if liq_result == 1:
        let (positions_ids_len : felt, positions_ids : Positions*) = IAccount.return_array_ids(
            contract_address=public_address
        )
        liquidate(positions_ids_len, positions_ids)
        return (1)
    else:
        return (0)
    end
end

func liquidate{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    positions_len : felt, positions : PriceData*
) -> (res : felt):
    alloc_locals
    # Check if the list is empty
    if positions_len == 0:
        return (1)
    end

    liquidate_position(id)

    return liquidate(positions_len - 1, positions + Positions.SIZE)
end

@contract_interface
namespace IAccount:
    func return_array() -> (array_list_len : felt, array_list : OrderDetails*):
    end

    func return_array_id() -> (array_list_len : felt, array_list : felt*):
    end

    func liquidate_position(id : felt) -> ():
    end
end

@contract_interface
namespace IAsset:
    func getAsset(id : felt) -> (currAsset : Asset):
    end
end
