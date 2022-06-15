%lang starknet

# @notice struct to store details of markets
struct Market:
    member asset : felt
    member assetCollateral : felt
    member leverage : felt
    member tradable : felt
end


# Struct to pass the order
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



# Struct to pass signatures to this contract
struct Signature:
    member r_value : felt
    member s_value : felt
end



# status 0: initialized
# status 1: partial
# status 2: executed
# status 3: close partial
# status 4: close
# status 5: toBeLiquidated
# status 6: fullyLiquidated
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
end

# status 0: initialized
# status 1: partial
# status 2: executed
# status 3: close partial
# status 4: close
# status 5: toBeLiquidated
# status 6: fullyLiquidated
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

struct CollateralBalance:
    member assetID : felt
    member balance : felt
end