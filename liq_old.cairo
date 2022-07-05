# %lang starknet

# %builtins pedersen range_check ecdsa

# from starkware.cairo.common.registers import get_fp_and_pc
# from starkware.starknet.common.syscalls import get_contract_address
# from starkware.cairo.common.bitwise import bitwise_and
# from starkware.cairo.common.math import (
#     assert_not_zero,
#     assert_nn,
#     assert_le,
#     assert_in_range,
#     assert_nn_le,
# )
# from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
# from starkware.cairo.common.signature import verify_ecdsa_signature
# from starkware.cairo.common.math_cmp import is_le
# from starkware.cairo.common.hash import hash2
# from starkware.starknet.common.syscalls import get_caller_address
# from starkware.cairo.common.hash_state import hash_init, hash_finalize, hash_update
# from contracts.Math_64x61 import mul_fp, div_fp

# # @notice struct for passing the order request to Account Contract
# # status 0: initialized
# # status 1: partial
# # status 2: executed
# # status 3: close partial
# # status 4: close
# struct OrderDetailsWithIDs:
#     member orderID : felt
#     member assetID : felt
#     member collateralID : felt
#     member price : felt
#     member executionPrice : felt
#     member positionSize : felt
#     member orderType : felt
#     member direction : felt
#     member portionExecuted : felt
#     member status : felt
#     member marginAmount : felt
#     member borrowedAmount : felt
# end

# # @notice struct to pass price data to the contract
# struct PriceData:
#     member assetID : felt
#     member collateralID : felt
#     member price : felt
# end

# # @notice Variable to set maintance margin
# @storage_var
# func maintanence_margin() -> (res : felt):
# end

# # @notice Stores the address of AdminAuth contract
# @storage_var
# func auth_address() -> (contract_address : felt):
# end

# #################
# # To be removed #
# @storage_var
# func temp_margin() -> (margin : felt):
# end

# @storage_var
# func pnl_curr() -> (pnl_curr : felt):
# end

# @storage_var
# func num() -> (num : felt):
# end

# @storage_var
# func den() -> (den : felt):
# end

# #################

# @constructor
# func constructor{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
#     _maintanence_margin : felt, _auth_address : felt
# ):
#     auth_address.write(_auth_address)
#     maintanence_margin.write(_maintanence_margin)

# return ()
# end

# ####################
# # To be removed    #
# @view
# func return_margin{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
#     res : felt
# ):
#     let (margin) = temp_margin.read()
#     return (res=margin)
# end

# @view
# func return_pnl{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
#     res : felt
# ):
#     let (pnl) = pnl_curr.read()
#     return (res=pnl)
# end

# @view
# func return_num{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
#     res : felt
# ):
#     let (numerator) = num.read()
#     return (res=numerator)
# end

# @view
# func return_den{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
#     res : felt
# ):
#     let (denominator) = den.read()
#     return (res=denominator)
# end
# #####################

# # @notice Function to set the maintainence margin requirement
# # @param _maintanence_margin - Value in 64x61
# @external
# func set_maintanence_margin{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
#     _maintanence_margin
# ):
#     alloc_locals
#     # Auth Check
#     let (caller) = get_caller_address()
#     let (auth_addr) = auth_address.read()

# let (access) = IAdminAuth.get_admin_mapping(
#         contract_address=auth_addr, address=caller, action=0
#     )
#     assert_not_zero(access)

# with_attr error_message("Invalid maintanence margin"):
#         assert_nn_le(_maintanence_margin, 2305843009213693952)
#     end

# return ()
# end

# # @notice Function that is called recursively by check_recurse
# # @param account_address - Account address of the user
# # @param collateral_id - Id of the margin collateral
# # @param positions_len - Length of the positions array
# # @param postions - Array with all the position details
# # @param prices_len - Length of the prices array
# # @param prices - Array with all the price details
# # @param maintanence_total_num - margin + pnl of the positions recursed over
# # @param maintanence_total_den - curr_price * portionExecuted of the positions recursed over
# # @returns res - 1 if positions are marked to be liquidated
# func check_liquidation_recurse{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
#     account_address : felt,
#     collateral_id : felt,
#     positions_len : felt,
#     positions : OrderDetailsWithIDs*,
#     prices_len : felt,
#     prices : PriceData*,
#     maintanence_total_num : felt,
#     maintanence_total_den : felt,
# ) -> (res : felt):
#     alloc_locals
#     # Check if the list is empty, if yes return 1
#     if positions_len == 0:
#         let (user_balance) = IAccount.get_balance(
#             contract_address=account_address, assetID_=collateral_id
#         )
#         local maintanence_total_num = maintanence_total_num + user_balance
#         let (account_margin) = div_fp(maintanence_total_num, maintanence_total_den)

# # To Remove
#         ######################
#         temp_margin.write(account_margin)
#         ######################
#         let (minimum_margin) = maintanence_margin.read()
#         let (is_liquidation) = is_le(account_margin, minimum_margin)
#         return (is_liquidation)
#     end

# # Create a struct object for the order
#     tempvar order_details : OrderDetailsWithIDs = OrderDetailsWithIDs(
#         orderID=[positions].orderID,
#         assetID=[positions].assetID,
#         collateralID=[positions].collateralID,
#         price=[positions].price,
#         executionPrice=[positions].executionPrice,
#         positionSize=[positions].positionSize,
#         orderType=[positions].orderType,
#         direction=[positions].direction,
#         portionExecuted=[positions].portionExecuted,
#         status=[positions].status,
#         marginAmount=[positions].marginAmount,
#         borrowedAmount=[positions].borrowedAmount
#         )

# tempvar asset_price : PriceData = PriceData(
#         assetID=[prices].assetID,
#         collateralID=[prices].collateralID,
#         price=[prices].price
#         )

# with_attr error_message("assetID and collateralID do not match"):
#         assert order_details.assetID = asset_price.assetID
#         assert order_details.collateralID = asset_price.collateralID
#     end

# with_attr error("price is invalid or the array is out of bounds"):
#         assert_nn(asset_price.price)
#         assert_not_zero(asset_price.price)
#     end

# local pnl : felt

# if order_details.direction == 1:
#         let (pnl_temp) = mul_fp(
#             asset_price.price - order_details.executionPrice, order_details.portionExecuted
#         )
#         pnl = pnl_temp
#     else:
#         let (pnl_temp) = mul_fp(
#             order_details.executionPrice - asset_price.price, order_details.portionExecuted
#         )
#         pnl = pnl_temp
#     end

# local maintanence_num = order_details.marginAmount + pnl
#     let (maintanence_den) = mul_fp(asset_price.price, order_details.portionExecuted)

# # ### To be removed ###
#     pnl_curr.write(pnl)
#     num.write(maintanence_num)
#     den.write(maintanence_den)
#     #####################
#     return check_liquidation_recurse(
#         account_address=account_address,
#         collateral_id=collateral_id,
#         positions_len=positions_len - 1,
#         positions=positions + OrderDetailsWithIDs.SIZE,
#         prices_len=prices_len - 1,
#         prices=prices + PriceData.SIZE,
#         maintanence_total_num=maintanence_total_num + maintanence_num,
#         maintanence_total_den=maintanence_total_den + maintanence_den,
#     )
# end

# # @notice Function to check and mark the positions to be liquidated
# # @param account_address - Account address of the user
# # @param prices_len - Length of the prices array
# # @param prices - Array with all the price details
# # @param collateral_id - Id of the margin collateral
# # @returns res - 1 if positions are marked to be liquidated
# @external
# func check_liquidation{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
#     account_address : felt, prices_len : felt, prices : PriceData*, collateral_id : felt
# ) -> (res : felt):
#     alloc_locals

# # Check if the list is empty
#     with_attr error_message("Invalid Input"):
#         assert_not_zero(prices_len)
#     end

# let (positions_len : felt, positions : OrderDetailsWithIDs*) = IAccount.return_array(
#         contract_address=account_address, collateral_id=collateral_id
#     )

# with_attr error_message("Position array length is 0"):
#         assert_not_zero(positions_len)
#         assert positions_len = prices_len
#     end

# let (liq_result) = check_liquidation_recurse(
#         account_address=account_address,
#         collateral_id=collateral_id,
#         positions_len=positions_len,
#         positions=positions,
#         prices_len=prices_len,
#         prices=prices,
#         maintanence_total_num=0,
#         maintanence_total_den=0,
#     )

# return (liq_result)
#     # if liq_result == 1:
#     #     liquidate(account_address, positions_len, positions)
#     #     return (1)
#     # else:
#     #     return (0)
#     # end
# end

# # @notice Internal function to mark the positions to be liquidated
# # @param account_address - Account address of the user
# # @param positions_len - Length of the positions array
# # @param postions - Array with all the position details
# func liquidate{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
#     account_address : felt, positions_len : felt, positions : OrderDetailsWithIDs*
# ) -> (res : felt):
#     alloc_locals
#     # Check if the list is empty
#     if positions_len == 0:
#         return (1)
#     end

# # Create a struct object for the order
#     tempvar order_details : OrderDetailsWithIDs = OrderDetailsWithIDs(
#         orderID=[positions].orderID,
#         assetID=[positions].assetID,
#         collateralID=[positions].collateralID,
#         price=[positions].price,
#         executionPrice=[positions].executionPrice,
#         positionSize=[positions].positionSize,
#         orderType=[positions].orderType,
#         direction=[positions].direction,
#         portionExecuted=[positions].portionExecuted,
#         status=[positions].status,
#         marginAmount=[positions].marginAmount,
#         borrowedAmount=[positions].borrowedAmount
#         )

# IAccount.liquidate_position(contract_address=account_address, id=order_details.orderID)

# return liquidate(account_address, positions_len - 1, positions + OrderDetailsWithIDs.SIZE)
# end

# # @notice Account interface
# @contract_interface
# namespace IAccount:
#     func return_array(collateral_id : felt) -> (
#         array_list_len : felt, array_list : OrderDetailsWithIDs*
#     ):
#     end

# func liquidate_position(id : felt) -> ():
#     end

# func get_balance(assetID_ : felt) -> (res : felt):
#     end
# end

# # @notice AdminAuth interface
# @contract_interface
# namespace IAdminAuth:
#     func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
#     end
# end
