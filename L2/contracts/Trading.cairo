%lang starknet

%builtins pedersen range_check ecdsa

from contracts.DataTypes import OrderRequest, OrderDetails, Signature, Market, MultipleOrder, Asset
from contracts.Constants import (
    Asset_INDEX,
    Market_INDEX,
    TradingFees_INDEX,
    Holding_INDEX,
    FeeBalance_INDEX,
    LiquidityFund_INDEX,
    InsuranceFund_INDEX,
    AccountRegistry_INDEX,
)
from contracts.interfaces.IAuthorizedRegistry import IAuthorizedRegistry
from contracts.interfaces.IAccount import IAccount
from contracts.interfaces.IAccountRegistry import IAccountRegistry
from contracts.interfaces.ITradingFees import ITradingFees
from contracts.interfaces.IAsset import IAsset
from contracts.interfaces.IHolding import IHolding
from contracts.interfaces.IFeeBalance import IFeeBalance
from contracts.interfaces.IMarkets import IMarkets
from contracts.interfaces.ILiquidityFund import ILiquidityFund
from contracts.interfaces.IInsuranceFund import IInsuranceFund
from contracts.Constants import AdminAuth_INDEX
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.math import assert_not_zero, assert_le, assert_in_range
from starkware.cairo.common.math import abs_value
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math_cmp import is_le
from contracts.Math_64x61 import Math64x61_mul, Math64x61_div

# @notice Stores the contract version
@storage_var
func contract_version() -> (version : felt):
end

# @notice Stores the address of Authorized Registry contract
@storage_var
func registry_address() -> (contract_address : felt):
end

@storage_var
func net_acc() -> (res : felt):
end

###
@view
func return_net_acc{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    res : felt
):
    let (net_acc_) = net_acc.read()
    return (res=net_acc_)
end
####

# @notice Constructor of the smart-contract
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

# @notice Internal function called by execute_batch
# @param size - Size of the order to be executed
# @param ticker - The ticker of each order in the batch
# @param execution_price - Price at which the orders must be executed
# @param request_list_len - No of orders in the batch
# @param request_list - The batch of the orders
# @returns 1, if executed correctly
func check_and_execute{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    size : felt,
    assetID : felt,
    collateralID : felt,
    marketID : felt,
    execution_price : felt,
    request_list_len : felt,
    request_list : MultipleOrder*,
    sum : felt,
) -> (res : felt):
    alloc_locals

    let (registry) = registry_address.read()
    let (version) = contract_version.read()

    # Check if the list is empty, if yes return 1
    if request_list_len == 0:
        return (sum)
    end

    local margin_amount_
    local borrowed_amount_
    local average_execution_price

    # Create a struct object for the order
    tempvar temp_order : MultipleOrder = MultipleOrder(
        pub_key=[request_list].pub_key,
        sig_r=[request_list].sig_r,
        sig_s=[request_list].sig_s,
        orderID=[request_list].orderID,
        assetID=[request_list].assetID,
        collateralID=[request_list].collateralID,
        price=[request_list].price,
        orderType=[request_list].orderType,
        positionSize=[request_list].positionSize,
        direction=[request_list].direction,
        closeOrder=[request_list].closeOrder,
        leverage=[request_list].leverage,
        isLiquidation=[request_list].isLiquidation,
        liquidatorAddress=[request_list].liquidatorAddress,
        parentOrder=[request_list].parentOrder,
        side=[request_list].side
        )

    # Get asset and market addresses
    let (asset_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Asset_INDEX, version=version
    )
    let (market_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Market_INDEX, version=version
    )

    # If it's the first order in the array
    if assetID == 0:
        # Check if the asset is tradable
        let (asset : Asset) = IAsset.getAsset(contract_address=asset_address, id=temp_order.assetID)
        let (collateral : Asset) = IAsset.getAsset(
            contract_address=asset_address, id=temp_order.collateralID
        )
        let (market : Market) = IMarkets.getMarket(contract_address=market_address, id=marketID)

        with_attr error_message("asset is non tradable in trading contract."):
            assert_not_zero(asset.tradable)
        end

        with_attr error_message("asset is non collaterable in trading contract."):
            assert_not_zero(collateral.collateral)
        end

        with_attr error_message("market is non tradable in trading contract."):
            assert_not_zero(market.tradable)
        end

        with_attr error_message(
                "leverage is not less than currently allowed leverage of the asset"):
            assert_le(temp_order.leverage, asset.currently_allowed_leverage)
        end

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    end
    tempvar syscall_ptr = syscall_ptr
    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
    tempvar range_check_ptr = range_check_ptr

    # Check if the execution_price is correct
    if temp_order.orderType == 1:
        # if it's a limit order
        if temp_order.direction == 1:
            # if it's a long order
            with_attr error_message(
                    "limit-long order execution price should be less than limit price."):
                assert_le(execution_price, temp_order.price)
            end
            tempvar range_check_ptr = range_check_ptr
        else:
            # if it's a short order
            with_attr error_message(
                    "limit-short order limit price should be less than execution price."):
                assert_le(temp_order.price, execution_price)
            end
            tempvar range_check_ptr = range_check_ptr
        end
        tempvar range_check_ptr = range_check_ptr
    else:
        # if it's a market order, it must be within 2% of the index price
        let (two_percent) = Math64x61_mul(temp_order.price, 46116860184273879)
        tempvar lowerLimit = temp_order.price - two_percent
        tempvar upperLimit = temp_order.price + two_percent

        with_attr error_message("Execution price is not in range."):
            assert_in_range(execution_price, lowerLimit, upperLimit)
        end
        tempvar range_check_ptr = range_check_ptr
    end

    # Check if size is less than or equal to postionSize
    let (cmp_res) = is_le(size, temp_order.positionSize)

    local order_size

    if cmp_res == 1:
        # If yes, make the order_size to be size
        assert order_size = size
    else:
        # If no, make order_size to be the positionSize̦
        assert order_size = temp_order.positionSize
    end

    local sum_temp

    if temp_order.direction == 1:
        assert sum_temp = sum + order_size
    else:
        assert sum_temp = sum - order_size
    end

    let (holding_address) = IAuthorizedRegistry.get_contract_address(
        contract_address=registry, index=Holding_INDEX, version=version
    )
    # If the order is to be opened
    if temp_order.closeOrder == 0:
        # Get the fees from Trading Fee contract
        let (trading_fees_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=TradingFees_INDEX, version=version
        )

        let (fees_rate) = ITradingFees.get_user_fee_and_discount(
            contract_address=trading_fees_address,
            address_=temp_order.pub_key,
            side_=temp_order.side,
        )

        # Get order details
        let (order_details : OrderDetails) = IAccount.get_order_data(
            contract_address=temp_order.pub_key, order_ID=temp_order.orderID
        )
        let margin_amount = order_details.marginAmount
        let borrowed_amount = order_details.borrowedAmount

        # Add user to account registry if user already not added
        let (account_registry_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=AccountRegistry_INDEX, version=version
        )
        let (present) = IAccountRegistry.is_registered_user(
            contract_address=account_registry_address, address_=temp_order.pub_key
        )
        if present == 0:
            IAccountRegistry.add_to_account_registry(
                contract_address=registry, address_=temp_order.pub_key
            )
        end
        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr

        # calculate avg execution price
        if order_details.executionPrice == 0:
            assert average_execution_price = execution_price
            tempvar range_check_ptr = range_check_ptr
        else:
            let (portion_executed_value) = Math64x61_mul(
                order_details.portionExecuted, order_details.executionPrice
            )
            let (current_order_value) = Math64x61_mul(order_size, execution_price)
            let cumulative_order_value = portion_executed_value + current_order_value
            let cumulative_order_size = order_details.portionExecuted + order_size
            let (price) = Math64x61_div(cumulative_order_value, cumulative_order_size)
            assert average_execution_price = price
            tempvar range_check_ptr = range_check_ptr
        end

        let (leveraged_position_value) = Math64x61_mul(order_size, execution_price)
        let (total_position_value) = Math64x61_div(leveraged_position_value, temp_order.leverage)
        tempvar amount_to_be_borrowed = leveraged_position_value - total_position_value

        # Calculate borrowed and margin amounts to be stored in account contract
        margin_amount_ = margin_amount + total_position_value
        borrowed_amount_ = borrowed_amount + amount_to_be_borrowed

        let (user_balance) = IAccount.get_balance(
            contract_address=temp_order.pub_key, assetID_=temp_order.collateralID
        )

        # Calculate the fees for the order
        let (fees) = Math64x61_mul(fees_rate, leveraged_position_value)

        # Calculate the total amount by adding fees
        tempvar total_amount = total_position_value + fees

        # User must be able to pay the amount
        with_attr error_message(
                "User balance is less than value of the position in trading contract."):
            assert_le(total_amount, user_balance)
        end

        # Deduct the amount from account contract
        IAccount.transfer_from(
            contract_address=temp_order.pub_key,
            assetID_=temp_order.collateralID,
            amount=total_amount,
        )

        # Update the fees to be paid by user in fee balance contract
        let (fees_balance_address) = IAuthorizedRegistry.get_contract_address(
            contract_address=registry, index=FeeBalance_INDEX, version=version
        )
        IFeeBalance.update_fee_mapping(
            contract_address=fees_balance_address,
            address=temp_order.pub_key,
            assetID_=temp_order.collateralID,
            fee_to_add=fees,
        )

        # Deduct the amount from liquidity funds if order is leveraged
        let (is_non_leveraged) = is_le(temp_order.leverage, 2305843009213693952)

        if is_non_leveraged == 0:
            let (liquidity_fund_address) = IAuthorizedRegistry.get_contract_address(
                contract_address=registry, index=LiquidityFund_INDEX, version=version
            )
            ILiquidityFund.withdraw(
                contract_address=liquidity_fund_address,
                asset_id_=temp_order.collateralID,
                amount=amount_to_be_borrowed,
                position_id_=temp_order.orderID,
            )
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        else:
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr
        end
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr

        # Deposit the funds taken from the user and liquidity fund
        IHolding.deposit(
            contract_address=holding_address,
            asset_id_=temp_order.collateralID,
            amount=leveraged_position_value,
        )

        tempvar syscall_ptr = syscall_ptr
        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
        tempvar range_check_ptr = range_check_ptr
    else:
        # If it's a close order or a liquidation order or deleveraging order
        with_attr error_message(
                "parentOrder field of closing order request is zero in trading contract."):
            assert_not_zero(temp_order.parentOrder)
        end

        # Get order details
        let (order_details : OrderDetails) = IAccount.get_order_data(
            contract_address=temp_order.pub_key, order_ID=temp_order.parentOrder
        )

        with_attr error_message("parentOrder doesn't exist"):
            assert_not_zero(order_details.assetID)
        end

        let margin_amount = order_details.marginAmount
        let borrowed_amount = order_details.borrowedAmount
        average_execution_price = order_details.executionPrice

        local diff
        local actual_execution_price

        # current order is short order
        if temp_order.direction == 0:
            # Open order was a long order
            actual_execution_price = execution_price
            diff = execution_price - order_details.executionPrice
        else:
            # Open order was a short order
            diff = order_details.executionPrice - execution_price
            actual_execution_price = order_details.executionPrice + diff
        end

        # Calculate pnl and net account value
        let (pnl) = Math64x61_mul(order_details.portionExecuted, diff)
        tempvar net_acc_value = margin_amount + pnl

        # Total value of the asset at current price
        let (leveraged_amount_out) = Math64x61_mul(order_size, actual_execution_price)

        # Calculate the amount that needs to be returned to liquidity fund
        let (percent_of_order) = Math64x61_div(order_size, order_details.portionExecuted)
        let (value_to_be_returned) = Math64x61_mul(borrowed_amount, percent_of_order)
        let (margin_to_be_reduced) = Math64x61_mul(margin_amount, percent_of_order)

        # Calculate new values for margin and borrowed amounts
        if temp_order.orderType == 4:
            borrowed_amount_ = borrowed_amount - leveraged_amount_out
            margin_amount_ = margin_amount
        else:
            borrowed_amount_ = borrowed_amount - value_to_be_returned
            margin_amount_ = margin_amount - margin_to_be_reduced
        end

        # Check if the position is to be liquidated
        let (not_liquidation) = is_le(order_details.status, 3)

        # If it's just a close order
        if not_liquidation == 1:
            # Deduct funds from holding contract
            IHolding.withdraw(
                contract_address=holding_address,
                asset_id_=temp_order.collateralID,
                amount=leveraged_amount_out,
            )

            # If no leverage is used
            # to64x61(1) == 2305843009213693952
            if temp_order.leverage == 2305843009213693952:
                tempvar syscall_ptr = syscall_ptr
                tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                tempvar range_check_ptr = range_check_ptr
            else:
                let (liquidity_fund_address) = IAuthorizedRegistry.get_contract_address(
                    contract_address=registry, index=LiquidityFund_INDEX, version=version
                )
                ILiquidityFund.deposit(
                    contract_address=liquidity_fund_address,
                    asset_id_=temp_order.collateralID,
                    amount=value_to_be_returned,
                    position_id_=temp_order.orderID,
                )
                tempvar syscall_ptr = syscall_ptr
                tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                tempvar range_check_ptr = range_check_ptr
            end
            tempvar syscall_ptr = syscall_ptr
            tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
            tempvar range_check_ptr = range_check_ptr

            # Check if the position is underwater
            let (is_loss) = is_le(net_acc_value, 0)

            if is_loss == 1:
                # If yes, deduct the difference from user's balance, can go negative
                IAccount.transfer_from(
                    contract_address=temp_order.pub_key,
                    assetID_=temp_order.collateralID,
                    amount=leveraged_amount_out - value_to_be_returned,
                )
                tempvar syscall_ptr = syscall_ptr
                tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                tempvar range_check_ptr = range_check_ptr
            else:
                # If not, transfer the remaining to user
                IAccount.transfer(
                    contract_address=temp_order.pub_key,
                    assetID_=temp_order.collateralID,
                    amount=leveraged_amount_out - value_to_be_returned,
                )
                tempvar syscall_ptr = syscall_ptr
                tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                tempvar range_check_ptr = range_check_ptr
            end
        else:
            # Liquidation order
            if order_details.status == 6:
                let (insurance_fund_address) = IAuthorizedRegistry.get_contract_address(
                    contract_address=registry, index=InsuranceFund_INDEX, version=version
                )

                # Withdraw the position from holding fund
                IHolding.withdraw(
                    contract_address=holding_address,
                    asset_id_=temp_order.collateralID,
                    amount=leveraged_amount_out,
                )

                let (liquidity_fund_address) = IAuthorizedRegistry.get_contract_address(
                    contract_address=registry, index=LiquidityFund_INDEX, version=version
                )

                # Return the borrowed fund to the Liquidity fund
                ILiquidityFund.deposit(
                    contract_address=liquidity_fund_address,
                    asset_id_=temp_order.collateralID,
                    amount=value_to_be_returned,
                    position_id_=temp_order.orderID,
                )

                # Check if the account value for the position is negative
                let (is_negative) = is_le(net_acc_value, 0)

                if is_negative == 1:
                    # Absolute value of the acc value
                    let (deficit) = abs_value(net_acc_value)

                    # Get the user balance
                    let (user_balance) = IAccount.get_balance(
                        contract_address=temp_order.pub_key, assetID_=temp_order.collateralID
                    )

                    # Check if the user's balance can cover the deficit
                    let (is_payable) = is_le(deficit, user_balance)

                    if is_payable == 1:
                        # Transfer the full amount from the user
                        IAccount.transfer_from(
                            contract_address=temp_order.pub_key,
                            assetID_=temp_order.collateralID,
                            amount=deficit,
                        )
                        tempvar syscall_ptr = syscall_ptr
                        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                        tempvar range_check_ptr = range_check_ptr
                    else:
                        # Transfer the partial amount from the user
                        IAccount.transfer_from(
                            contract_address=temp_order.pub_key,
                            assetID_=temp_order.collateralID,
                            amount=user_balance,
                        )

                        # Transfer the remaining amount from Insurance Fund
                        IInsuranceFund.withdraw(
                            contract_address=insurance_fund_address,
                            asset_id_=temp_order.collateralID,
                            amount=deficit - user_balance,
                            position_id_=temp_order.orderID,
                        )

                        tempvar syscall_ptr = syscall_ptr
                        tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                        tempvar range_check_ptr = range_check_ptr
                    end
                else:
                    # Deposit the user's remaining margin in Insurance Fund
                    IInsuranceFund.deposit(
                        contract_address=insurance_fund_address,
                        asset_id_=temp_order.collateralID,
                        amount=net_acc_value,
                        position_id_=temp_order.orderID,
                    )
                    tempvar syscall_ptr = syscall_ptr
                    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                    tempvar range_check_ptr = range_check_ptr
                end
            else:
                # Deleveraging order
                if order_details.status == 5:
                    # Withdraw the position from holding fund
                    let (holding_address) = IAuthorizedRegistry.get_contract_address(
                        contract_address=registry, index=Holding_INDEX, version=version
                    )

                    IHolding.withdraw(
                        contract_address=holding_address,
                        asset_id_=temp_order.collateralID,
                        amount=leveraged_amount_out,
                    )

                    let (liquidity_fund_address) = IAuthorizedRegistry.get_contract_address(
                        contract_address=registry, index=LiquidityFund_INDEX, version=version
                    )

                    # Return the borrowed fund to the Liquidity fund
                    ILiquidityFund.deposit(
                        contract_address=liquidity_fund_address,
                        asset_id_=temp_order.collateralID,
                        amount=leveraged_amount_out,
                        position_id_=temp_order.orderID,
                    )

                    tempvar syscall_ptr = syscall_ptr
                    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                    tempvar range_check_ptr = range_check_ptr
                else:
                    # The position is not marked as "to be deleveraged" aka status 5 and "to be liquidated" aka status 6
                    with_attr error_message(
                            "The position cannot be deleveraged or liqudiated w/o status 5 or 6"):
                        assert 1 = 0
                    end
                    tempvar syscall_ptr = syscall_ptr
                    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
                    tempvar range_check_ptr = range_check_ptr
                end
            end
        end
    end

    # Create a temporary order object
    let temp_order_request : OrderRequest = OrderRequest(
        orderID=temp_order.orderID,
        assetID=temp_order.assetID,
        collateralID=temp_order.collateralID,
        price=temp_order.price,
        orderType=temp_order.orderType,
        positionSize=temp_order.positionSize,
        direction=temp_order.direction,
        closeOrder=temp_order.closeOrder,
        leverage=temp_order.leverage,
        isLiquidation=temp_order.isLiquidation,
        liquidatorAddress=temp_order.liquidatorAddress,
        parentOrder=temp_order.parentOrder,
    )

    # Create a temporary signature object
    let temp_signature : Signature = Signature(r_value=temp_order.sig_r, s_value=temp_order.sig_s)

    tempvar syscall_ptr = syscall_ptr
    tempvar pedersen_ptr : HashBuiltin* = pedersen_ptr
    tempvar range_check_ptr = range_check_ptr

    # Call the account contract to initialize the order
    IAccount.execute_order(
        contract_address=temp_order.pub_key,
        request=temp_order_request,
        signature=temp_signature,
        size=order_size,
        execution_price=average_execution_price,
        margin_amount=margin_amount_,
        borrowed_amount=borrowed_amount_,
    )

    # If it's the first order in the array
    if assetID == 0:
        # Recursive call with the ticker and price to compare against
        return check_and_execute(
            size,
            temp_order.assetID,
            temp_order.collateralID,
            marketID,
            execution_price,
            request_list_len - 1,
            request_list + MultipleOrder.SIZE,
            sum_temp,
        )
    end

    # Assert that the order has the same ticker and price as the first order
    with_attr error_message("assetID is not same as opposite order's assetID in trading contract."):
        assert assetID = temp_order.assetID
    end

    with_attr error_message(
            "collateralID is not same as opposite order's collateralID in trading contract."):
        assert collateralID = temp_order.collateralID
    end

    # Recursive Call
    return check_and_execute(
        size,
        assetID,
        collateralID,
        marketID,
        execution_price,
        request_list_len - 1,
        request_list + MultipleOrder.SIZE,
        sum_temp,
    )
end

# @notice Function to execute multiple orders in a batch
# @param size - Size of the order to be executed
# @param execution_price - Price at which the orders must be executed
# @param request_list_len - No of orders in the batch
# @param request_list - The batch of the orders
# @returns res - 1 if executed correctly
@external
func execute_batch{
    syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*
}(
    size : felt,
    execution_price : felt,
    marketID : felt,
    request_list_len : felt,
    request_list : MultipleOrder*,
) -> (res : felt):
    alloc_locals

    # Recursively loop through the orders in the batch
    let (result) = check_and_execute(
        size, 0, 0, marketID, execution_price, request_list_len, request_list, 0
    )

    # Check if every order has a counter order
    with_attr error_message("check and execute returned non zero integer."):
        assert result = 0
    end
    return (1)
end
