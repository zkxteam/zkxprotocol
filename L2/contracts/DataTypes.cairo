%lang starknet

# @notice struct to store details of markets
struct Market:
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
    member isLiquidation : felt
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
    member isLiquidation : felt
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
