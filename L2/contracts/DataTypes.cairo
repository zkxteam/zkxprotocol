%lang starknet

# @notice struct to store details of markets
struct Market:
    member asset : felt
    member assetCollateral : felt
    member leverage : felt
    member tradable : felt
end

# @notice struct to store details of markets with IDs
struct MarketWID:
    member id : felt
    member asset : felt
    member assetCollateral : felt
    member leverage : felt
    member tradable : felt
end

# @notice struct to store details of assets
struct Asset:
    member asset_version : felt
    member ticker : felt
    member short_name : felt
    member tradable : felt
    member collateral : felt
    member token_decimal : felt
    member metadata_id : felt
    member ttl : felt
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

# @notice struct to store details of assets with IDs
struct AssetWID:
    member id : felt
    member asset_version : felt
    member ticker : felt
    member short_name : felt
    member tradable : felt
    member collateral : felt
    member token_decimal : felt
    member metadata_id : felt
    member ttl : felt
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

# @notice Struct to store base fee percentage for each tier for maker and taker
struct BaseFee:
    member numberOfTokens : felt
    member makerFee : felt
    member takerFee : felt
end

# @notice Struct to store discount percentage for each tier
struct Discount:
    member numberOfTokens : felt
    member discount : felt
end

# Struct to pass orders+signatures in a batch in the execute_batch fn
struct MultipleOrder:
    member pub_key : felt
    member sig_r : felt
    member sig_s : felt
    member orderID : felt
    member assetID : felt
    member collateralID : felt
    member price : felt
    member orderType : felt
    member positionSize : felt
    member direction : felt
    member closeOrder : felt
    member leverage : felt
    member liquidatorAddress : felt
    member parentOrder : felt
    member side : felt
end

# @notice struct to pass price data to the contract
struct PriceData:
    member assetID : felt
    member collateralID : felt
    member assetPrice : felt
    member collateralPrice : felt
end

# @notice struct for passing the order request to Account Contract
struct OrderRequest:
    member orderID : felt
    member assetID : felt
    member collateralID : felt
    member price : felt
    member orderType : felt
    member positionSize : felt
    member direction : felt
    member closeOrder : felt
    member leverage : felt
    member liquidatorAddress : felt
    member parentOrder : felt
end

# @notice struct for storing the order data to Account Contract
struct OrderDetails:
    member assetID : felt
    member collateralID : felt
    member price : felt
    member executionPrice : felt
    member positionSize : felt
    member orderType : felt
    member direction : felt
    member portionExecuted : felt
    member status : felt
    member marginAmount : felt
    member borrowedAmount : felt
    member leverage : felt
end

# Struct for passing signature to Account Contract
struct Signature:
    member r_value : felt
    member s_value : felt
end

# Struct for Withdrawal Request
# status 0: initiated
# status 1: consumed
struct WithdrawalRequest:
    member user_l1_address : felt
    member user_l2_address : felt
    member ticker : felt
    member amount : felt
    member timestamp : felt
    member status : felt
    member L1_fee_amount : felt
    member L1_fee_ticker : felt
end

# Struct to pass the transactions to the contract
struct Message:
    member sender : felt
    member to : felt
    member selector : felt
    member calldata : felt*
    member calldata_size : felt
    member nonce : felt
end

# status 0: initiated
# status 1: partial
# status 2: executed
# status 3: close partial
# status 4: close
# status 5: toBeDeleveraged
# status 6: toBeLiquidated
# status 7: fullyLiquidated
struct OrderDetailsWithIDs:
    member orderID : felt
    member assetID : felt
    member collateralID : felt
    member price : felt
    member executionPrice : felt
    member positionSize : felt
    member orderType : felt
    member direction : felt
    member portionExecuted : felt
    member status : felt
    member marginAmount : felt
    member borrowedAmount : felt
end

# Struct to store collateral balances
struct CollateralBalance:
    member assetID : felt
    member balance : felt
end

# Struct to store withdrawal details
# status 0: initiated
# status 1: withdrawal succcessful
struct WithdrawalHistory:
    member collateral_id : felt
    member amount : felt
    member timestamp : felt
    member node_operator_L1_address : felt
    member node_operator_L2_address : felt
    member L1_fee_amount : felt
    member L1_fee_collateral_id : felt
    member L2_fee_amount : felt
    member L2_fee_collateral_id : felt
    member status : felt
end

# Struct for message to consume for quoting fee in L1
struct QuoteL1Message:
    member user_l1_address : felt
    member ticker : felt
    member amount : felt
    member timestamp : felt
    member L1_fee_amount : felt
    member L1_fee_ticker : felt
end
