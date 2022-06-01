%lang starknet
%builtins pedersen range_check ecdsa

from starkware.cairo.common.alloc import alloc
from starkware.starknet.common.messages import send_message_to_l1
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address

const ADD_ASSET = 1
const REMOVE_ASSET = 2

#
# Structs
#

# @notice struct to store details of assets
struct Asset:
    member asset_version : felt
    member ticker : felt
    member short_name : felt
    member tradable : felt
    member collateral : felt
    member token_decimal : felt
    member metadata_id : felt
    member tick_size : felt
    member step_size : felt
    member minimum_order_size : felt
    member minimum_leverage : felt
    member maximum_leverage : felt
    member currently_allowed_leverage : felt
    member maintenance_margin_fraction : felt
    member initial_margin_fraction : felt
    member incremental_initial_margin_fraction : felt
    member incremental_position_size : felt
    member baseline_position_size : felt
    member maximum_position_size : felt
end

#
# Storage
#

# @notice Stores the address of AdminAuth contract
@storage_var
func auth_address() -> (contract_address : felt):
end

# @notice stores the address of L1 zkx contract
@storage_var
func L1_zkx_address() -> (res : felt):
end

# @notice stores the address of risk management contract
@storage_var
func risk_management_address() -> (res : felt):
end

# @notice stores the version of the asset contract
@storage_var
func version() -> (res : felt):
end

# @notice Mapping between asset ID and Asset data
@storage_var
func asset(id : felt) -> (res : Asset):
end

#
# Setters
#

# @notice set L1 zkx contract address function
# @param address - L1 zkx contract address as an argument
@external
func set_L1_zkx_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    l1_zkx_address : felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=1
    )
    assert_not_zero(access)

    L1_zkx_address.write(value=l1_zkx_address)
    return ()
end

#
# Getters
#

# @notice get L1 zkx contract address function
@view
func get_L1_zkx_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (res) = L1_zkx_address.read()
    return (res=res)
end

# @notice Getter function for Assets
# @param id - random string generated by zkxnode's mongodb
# @returns currAsset - Returns the requested asset
@view
func getAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(id : felt) -> (
    currAsset : Asset
):
    let (currAsset) = asset.read(id=id)
    return (currAsset)
end

# @notice Return the maintanence margin for the asset
# @param id - Id of the asset
# @return maintanence_margin - Returns the maintanence margin of the asset
@view
func get_maintanence_margin{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt
) -> (maintanence_margin : felt):
    let (curr_asset) = asset.read(id=id)
    return (curr_asset.maintenance_margin_fraction)
end

# @notice Getter function for getting version
# @returns  - Returns the version
@view
func get_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    version : felt
):
    let (res) = version.read()
    return (version=res)
end

#
# Constructor
#

# @notice Constructor of the smart-contract
# @param _authAddress Address of the adminAuth contract
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    _authAddress : felt, _riskManagementAddress : felt
):
    auth_address.write(value=_authAddress)
    risk_management_address.write(value=_riskManagementAddress)
    return ()
end

#
# Business logic
#

# @notice Add asset function
# @param id - random string generated by zkxnode's mongodb
# @param Asset - Asset struct variable with the required details
@external
func addAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt, newAsset : Asset
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=1
    )
    assert_not_zero(access)

    asset.write(id=id, value=newAsset)

    updateAssetListInL1(assetId=id, ticker=newAsset.ticker, action=ADD_ASSET)

    return ()
end

# @notice Remove asset function
# @param id - random string generated by zkxnode's mongodb
@external
func removeAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(id : felt):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=1
    )
    assert_not_zero(access)

    let (_asset : Asset) = asset.read(id=id)

    asset.write(
        id=id,
        value=Asset(asset_version=0, ticker=0, short_name=0, tradable=0, collateral=0, token_decimal=0,
        metadata_id=0, tick_size=0, step_size=0, minimum_order_size=0, minimum_leverage=0, maximum_leverage=0,
        currently_allowed_leverage=0, maintenance_margin_fraction=0, initial_margin_fraction=0, incremental_initial_margin_fraction=0,
        incremental_position_size=0, baseline_position_size=0, maximum_position_size=0),
    )

    updateAssetListInL1(assetId=id, ticker=_asset.ticker, action=REMOVE_ASSET)

    return ()
end

# @notice Modify core settings of asset function
# @param id - random string generated by zkxnode's mongodb
# @param short_name - new short_name for the asset
# @param tradable - new tradable flag value for the asset
# @param collateral - new collateral falg value for the asset
# @param token_decimal - It represents decimal point value of the token
# @param metadata_id -ID generated by asset metadata collection in zkx node
@external
func modify_core_settings{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt,
    short_name : felt,
    tradable : felt,
    collateral : felt,
    token_decimal : felt,
    metadata_id : felt,
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=1
    )
    assert_not_zero(access)

    let (_asset : Asset) = asset.read(id=id)

    asset.write(
        id=id,
        value=Asset(asset_version=_asset.asset_version, ticker=_asset.ticker, short_name=short_name, tradable=tradable,
        collateral=collateral, token_decimal=token_decimal, metadata_id=metadata_id, tick_size=_asset.tick_size, step_size=_asset.step_size,
        minimum_order_size=_asset.minimum_order_size, minimum_leverage=_asset.minimum_leverage, maximum_leverage=_asset.maximum_leverage,
        currently_allowed_leverage=_asset.currently_allowed_leverage, maintenance_margin_fraction=_asset.maintenance_margin_fraction,
        initial_margin_fraction=_asset.initial_margin_fraction, incremental_initial_margin_fraction=_asset.incremental_initial_margin_fraction,
        incremental_position_size=_asset.incremental_position_size, baseline_position_size=_asset.baseline_position_size,
        maximum_position_size=_asset.maximum_position_size),
    )
    return ()
end

# @notice Modify core settings of asset function
# @param id - random string generated by zkxnode's mongodb
# @param tick_size - new tradable flag value for the asset
# @param step_size - new collateral flag value for the asset
# @param minimum_order_size - new minimum_order_size value for the asset
# @param minimum_leverage - new minimum_leverage value for the asset
# @param maximum_leverage - new maximum_leverage value for the asset
# @param currently_allowed_leverage - new currently_allowed_leverage value for the asset
# @param maintenance_margin_fraction - new maintenance_margin_fraction value for the asset
# @param initial_margin_fraction - new initial_margin_fraction value for the asset
# @param incremental_initial_margin_fraction - new incremental_initial_margin_fraction value for the asset
# @param incremental_position_size - new incremental_position_size value for the asset
# @param baseline_position_size - new baseline_position_size value for the asset
# @param maximum_position_size - new maximum_position_size value for the asset
@external
func modify_trade_settings{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    id : felt,
    tick_size : felt,
    step_size : felt,
    minimum_order_size : felt,
    minimum_leverage : felt,
    maximum_leverage : felt,
    currently_allowed_leverage : felt,
    maintenance_margin_fraction : felt,
    initial_margin_fraction : felt,
    incremental_initial_margin_fraction : felt,
    incremental_position_size : felt,
    baseline_position_size : felt,
    maximum_position_size : felt,
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (risk_management_addr) = risk_management_address.read()

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=1
    )
    if access == 0:
        assert caller = risk_management_addr
    end

    let (ver) = version.read()
    version.write(value=ver + 1)

    let (_asset : Asset) = asset.read(id=id)

    asset.write(
        id=id,
        value=Asset(asset_version=_asset.asset_version + 1, ticker=_asset.ticker, short_name=_asset.short_name, tradable=_asset.tradable,
        collateral=_asset.collateral, token_decimal=_asset.token_decimal, metadata_id=_asset.metadata_id, tick_size=tick_size, step_size=step_size,
        minimum_order_size=minimum_order_size, minimum_leverage=minimum_leverage, maximum_leverage=maximum_leverage,
        currently_allowed_leverage=currently_allowed_leverage, maintenance_margin_fraction=maintenance_margin_fraction,
        initial_margin_fraction=initial_margin_fraction, incremental_initial_margin_fraction=incremental_initial_margin_fraction,
        incremental_position_size=incremental_position_size, baseline_position_size=baseline_position_size, maximum_position_size=maximum_position_size),
    )
    return ()
end

# @notice Function to update asset list in L1
# @param assetId - random string generated by zkxnode's mongodb
# @param ticker - Name of the asset
func updateAssetListInL1{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    assetId : felt, ticker : felt, action : felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()

    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=1
    )
    assert_not_zero(access)

    # Send the add asset message.
    let (message_payload : felt*) = alloc()
    assert message_payload[0] = action
    assert message_payload[1] = ticker
    assert message_payload[2] = assetId

    let (L1_CONTRACT_ADDRESS) = get_L1_zkx_address()

    send_message_to_l1(to_address=L1_CONTRACT_ADDRESS, payload_size=3, payload=message_payload)

    return ()
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end
