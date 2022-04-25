%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address

# @notice Stores the address of AdminAuth contract
@storage_var
func auth_address() -> (contract_address : felt):
end

# @notice struct to store tier criteria
struct Tier_Details:
    member min_balance : felt
    member min_trading_vol : felt
    member discount : felt
end

# @notice struct to store access to trading functionalities
struct Trade_Details:
    member market : felt
    member limit : felt
    member stop : felt
end

# @notice Stores the base trading fees
# long position = (0 => fees)
# short position = (1 => fees)
@storage_var
func base_trading_fees(direction : felt) -> (values : felt):
end

# @notice Stores the criteria for assigning the user to a tier
@storage_var
func tier_criteria(tier_level : felt) -> (value : Tier_Details):
end

# @notice Stores the trading functionalities a tier user has access to
@storage_var
func trade_access(tier_level : felt) -> (value : Trade_Details):
end

# @notice Constructor for the smart-contract
# @param long_fees - Base fees for the long positions
# @param short_fees - Base fees for the short positions
# @param _authAddress - Address of the AdminAuth Contract
# @param tier_details1 - Struct object to init tier level 1
# @param tier_details2 - Struct object to init tier level 2
# @param tier_details3 - Struct object to init tier level 3
# @param trade_access1 - Struct object to init trade acccess for level 1
# @param trade_access2 - Struct object to init trade acccess for level 2
# @param trade_access3 - Struct object to init trade acccess for level 3
@constructor
func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    long_fees_new : felt,
    short_fees_new : felt,
    _authAddress : felt,
    tier_details1 : Tier_Details,
    tier_details2 : Tier_Details,
    tier_details3 : Tier_Details,
    trade_access1 : Trade_Details,
    trade_access2 : Trade_Details,
    trade_access3 : Trade_Details,
):
    # long position => 1.2
    base_trading_fees.write(direction=0, value=long_fees_new)
    # short position => 0.8
    base_trading_fees.write(direction=1, value=short_fees_new)

    # Set the tier criteria
    tier_criteria.write(tier_level=1, value=tier_details1)
    tier_criteria.write(tier_level=2, value=tier_details2)
    tier_criteria.write(tier_level=3, value=tier_details3)

    # Set the trade access for each criteria
    trade_access.write(tier_level=1, value=trade_access1)
    trade_access.write(tier_level=2, value=trade_access2)
    trade_access.write(tier_level=3, value=trade_access3)

    auth_address.write(value=_authAddress)
    return ()
end

# @notice Function to modify fees only callable by the admins with action access=2
# @param long_fees_mod - New fees for the long positions
# @param short_fees_mod - New fees for the short positions
@external
func update_fees{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    long_fees_mod : felt, short_fees_mod : felt
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=2
    )
    assert_not_zero(access)

    # Update the fees
    base_trading_fees.write(direction=0, value=long_fees_mod)
    base_trading_fees.write(direction=1, value=short_fees_mod)
    return ()
end

# @notice Function to modify tier details only callable by the admins with action access=2
# @param tier_level - Level of Tier to modify
# @param tier_criteria_- Struct object with modidified data
@external
func update_tier_criteria{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_level : felt, tier_criteria_new : Tier_Details
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=2
    )
    assert_not_zero(access)

    # Set the tier criteria
    tier_criteria.write(tier_level=tier_level, value=tier_criteria_new)
    return ()
end

# @notice Function to modify trade access only callable by the admins with action access=2
# @param tier_level - Level of Tier to modify
# @param tier_criteria_- Struct object with modidified data
@external
func update_trade_access{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_level : felt, trade_access_new : Trade_Details
):
    alloc_locals
    # Auth Check
    let (caller) = get_caller_address()
    let (auth_addr) = auth_address.read()
    let (access) = IAdminAuth.get_admin_mapping(
        contract_address=auth_addr, address=caller, action=2
    )
    assert_not_zero(access)

    # Set the tier criteria
    trade_access.write(tier_level=tier_level, value=trade_access_new)
    return ()
end

# @notice Getter function for tier details
@view
func get_tier_criteria{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_level : felt
) -> (tier_criteria_curr : Tier_Details):
    let (tier_criteria_curr) = tier_criteria.read(tier_level=tier_level)
    return (tier_criteria_curr)
end

# @notice Getter function for trade access details
@view
func get_trade_access{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    tier_level : felt
) -> (trade_access_curr : Trade_Details):
    let (trade_access_curr) = trade_access.read(tier_level=tier_level)
    return (trade_access_curr)
end

# @notice Getter function for fees
@view
func get_fees{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    long_fees : felt, short_fees : felt
):
    let (long_fees) = base_trading_fees.read(direction=0)
    let (short_fees) = base_trading_fees.read(direction=1)
    return (long_fees, short_fees)
end

# @notice AdminAuth interface
@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end
